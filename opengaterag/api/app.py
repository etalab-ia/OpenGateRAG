from importlib import import_module
import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import prometheus_client
from prometheus_client import CollectorRegistry, multiprocess
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from starlette.responses import Response

from opengaterag.api.utils.configuration import Configuration, get_configuration
from opengaterag.api.utils.lifespan import lifespan
from opengaterag.api.utils.variables import RouterName

logger = logging.getLogger(__name__)


def create_app(
    configuration: Configuration | None = None,
    skip_lifespan: bool = False,
) -> FastAPI:
    if configuration is None:
        configuration = get_configuration()

    _setup_sentry(configuration)

    app = FastAPI(
        title=configuration.settings.app_title,
        summary=configuration.settings.swagger_summary,
        version=configuration.settings.swagger_version,
        description=configuration.settings.swagger_description,
        terms_of_service=configuration.settings.swagger_terms_of_service,
        contact=configuration.settings.swagger_contact,
        license_info=configuration.settings.swagger_license_info,
        openapi_tags=configuration.settings.swagger_openapi_tags,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=None if skip_lifespan else lifespan,
    )
    _register_routers(app, configuration)
    _setup_monitoring(app, configuration)
    _setup_unified_docs(app, configuration)

    return app


def _setup_sentry(configuration: Configuration) -> None:
    if configuration.dependencies.sentry:
        logger.info("Initializing Sentry SDK.")
        sentry_sdk.init(**configuration.dependencies.sentry.model_dump())


def _setup_prometheus(app: FastAPI, include_in_schema: bool = True) -> None:
    app.instrumentator = Instrumentator().instrument(app=app)

    @app.get(path="/metrics", tags=[RouterName.MONITORING.title()], include_in_schema=include_in_schema)
    def metrics() -> Response:
        if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
        else:
            registry = prometheus_client.REGISTRY

        data = prometheus_client.generate_latest(registry)
        return Response(content=data, media_type=prometheus_client.CONTENT_TYPE_LATEST)


def _setup_unified_docs(app: FastAPI, configuration: Configuration) -> None:
    from opengaterag.docs.app import create_docs_app

    docs_app = create_docs_app(parent_app=app, configuration=configuration)
    app.mount(path="/", app=docs_app)


def _register_routers(app: FastAPI, configuration: Configuration) -> None:
    disabled_routers = set(configuration.settings.disabled_routers)
    hidden_routers = set(configuration.settings.hidden_routers)
    enabled_routers = (router for router in RouterName if router not in disabled_routers and router.module_path is not None)
    for enabled_router in enabled_routers:
        module = import_module(enabled_router.module_path)
        router = getattr(module, "router", None)
        if router is None:
            raise AttributeError(f"Module {enabled_router.module_path} has no 'router' attribute")
        include_in_schema = enabled_router not in hidden_routers
        app.include_router(router=router, include_in_schema=include_in_schema)


def _setup_monitoring(app: FastAPI, configuration: Configuration) -> None:
    if RouterName.MONITORING in configuration.settings.disabled_routers:
        return

    include_in_schema = RouterName.MONITORING not in configuration.settings.hidden_routers

    if configuration.settings.monitoring_prometheus_enabled:
        _setup_prometheus(app, include_in_schema=include_in_schema)

    @app.get(path="/health", tags=[RouterName.MONITORING.title()], include_in_schema=include_in_schema)
    def health() -> JSONResponse:
        return JSONResponse(content={"status": "ok"}, status_code=200)
