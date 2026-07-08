from enum import StrEnum
from functools import lru_cache, wraps
import logging
import os
from pathlib import Path
import re
from typing import Annotated, Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

from opengaterag.api.utils.elasticsearch import ElasticsearchIndexLanguage
from opengaterag.api.utils.variables import DEFAULT_APP_NAME, RouterName

# utils ----------------------------------------------------------------------------------------------------------------------------------------------


def custom_validation_error(suffix: str = ""):
    """
    Decorator to override Pydantic ValidationError to change error message.

    Args:
        url(Optional[str]): override Pydantic documentation URL by provided URL. If not provided, the error message will be the same as the original error message.
    """

    class ValidationError(Exception):
        def __init__(
            self, exc: PydanticValidationError, cls: BaseModel, base_url: str = "https://docs.opengatellm.org/configuration/configuration_file"
        ):
            super().__init__()
            error_content = exc.errors()

            def resolve_model_for_error(model: type[BaseModel], loc: tuple[Any, ...]):
                current_model = model
                documentation_url = base_url

                for idx, part in enumerate(loc):
                    if not isinstance(part, str):
                        continue
                    if part not in current_model.__pydantic_fields__:
                        break

                    field_info = current_model.__pydantic_fields__[part]

                    annotation = field_info.annotation
                    next_model = None
                    origin = get_origin(annotation)
                    args = get_args(annotation)
                    candidates = args if origin is not None else (annotation,)

                    for candidate in candidates:
                        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                            next_model = candidate
                            break

                    if next_model is None:
                        break

                    current_model = next_model
                    documentation_url = f"{base_url}#{current_model.__name__.lower()}{suffix}"

                return documentation_url

            message = str(exc)
            for error in error_content:
                loc = tuple(error.get("loc", ()))
                documentation_url = resolve_model_for_error(cls, loc)
                original_line = f"    For further information visit {error['url']}"
                replacement_line = f"    For further information visit {documentation_url}"
                message = message.replace(original_line, replacement_line, 1)

            self.message = message

        def __str__(self):
            return self.message

    def decorator(cls: type[BaseModel]):
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, **data):
            try:
                original_init(self, **data)
            except PydanticValidationError as e:
                raise ValidationError(exc=e, cls=cls) from None  # hide previous traceback

        cls.__init__ = new_init
        return cls

    return decorator


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


@custom_validation_error()
class ElasticsearchDependency(ConfigBaseModel):
    """
    Elasticsearch is a required dependency of OpenGateRAG. Elasticsearch is used as a vector store. If this dependency is provided, all documents endpoint are enabled.
    Pass all arguments of `elasticsearch.Elasticsearch` class, see https://elasticsearch-py.readthedocs.io/en/latest/api/elasticsearch.html for more information.
    Other arguments declared below are used to configure the Elasticsearch index.
    """

    index_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default="opengaterag", description="Name of the Elasticsearch index.", examples=["my_index"])  # fmt: off
    index_language: Annotated[ElasticsearchIndexLanguage, Field(default=ElasticsearchIndexLanguage.ENGLISH, description="Language of the Elasticsearch index.", examples=[ElasticsearchIndexLanguage.ENGLISH.value])]  # fmt: off
    number_of_shards: Annotated[int, Field(default=12, ge=1, le=75, description="Number of shards for the Elasticsearch index.", examples=[4])]
    number_of_replicas: Annotated[int, Field(default=1, ge=0, description="Number of replicas for the Elasticsearch index.", examples=[1])]
    refresh_interval: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^(-1|\d+(ms|s|m|h|d))$")] = Field(default="1s", description="Refresh interval for the Elasticsearch index", examples=["2s"])  # fmt: off


@custom_validation_error()
class OpengateLLMDependency(ConfigBaseModel):
    """
    OpengateLLM is a required dependency of OpenGateLLM. It is used to connect to the OpengateLLM API.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(..., description="URL of the OpengateLLM API.", examples=["https://opengatellm.com"])  # fmt: off
    model_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(..., description="Model of the vector store to be used to embed the text in the vector store.", examples=["text-embedding-3-small"])  # fmt: off
    model_vector_size: Annotated[int, Field(ge=1, description="Size of the vector to be used to embed the text in the vector store.", examples=[1536])]  # fmt: off
    public_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="Public URL of the OpengateLLM API to run swagger UI without CORS issues. If not provided, the public URL will be the same as the `url`.")  # fmt: off
    openapi_url: Annotated[str, Field(default="/openapi.json", description="Path, relative to `url`, where OpengateLLM exposes its OpenAPI schema. Used to build the unified API documentation.", examples=["/openapi.json"])]  # fmt: off

    @field_validator("public_url", mode="after")
    def set_public_url(cls, public_url: str | None) -> str:
        if public_url is None:
            return cls.url
        return public_url


@custom_validation_error()
class PostgresDependency(ConfigBaseModel):
    """
    Postgres is a required dependency of OpenGateRAG. In this section, you can pass all postgres python SDK arguments, see https://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-apihttps://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-api for more information.
    Only the `url` argument is required. The connection URL must use the asynchronous scheme, `postgresql+asyncpg://`. If you provide a standard `postgresql://` URL, it will be automatically converted to use asyncpg.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^postgresql\+asyncpg://")] = Field(..., description="PostgreSQL connection url.", examples=["postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"])  # fmt: off


@custom_validation_error()
class SentryDependency(ConfigBaseModel):
    """
    Sentry is an optional dependency of OpenGateLLM. Sentry helps you identify, diagnose, and fix errors in real-time.
    In this section, you can pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information.
    """

    pass
    # All args of pydantic sentry client is allowed


@custom_validation_error()
class Dependencies(ConfigBaseModel):
    elasticsearch: ElasticsearchDependency = Field(default=..., description="Elasticsearch is a required dependency of OpenGateRAG. Elasticsearch is used as a vector store. If this dependency is provided, all documents endpoint are enabled.")  # fmt: off
    opengatellm: OpengateLLMDependency = Field(..., description="OpengateLLM is a required dependency of OpenGateRAG to embed the text in the vector store and retrieve user information.")  # fmt: off
    postgres: PostgresDependency = Field(..., description="Postgres is a required dependency of OpenGateRAG to store API data.")  # fmt: off
    sentry: SentryDependency | None = Field(default=None, description="Sentry is an optional dependency of OpenGateRAG. Sentry helps you identify, diagnose, and fix errors in real-time.")  # fmt: off


# settings -------------------------------------------------------------------------------------------------------------------------------------------
class Tokenizer(StrEnum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


@custom_validation_error()
class Settings(ConfigBaseModel):
    """
    General settings configuration fields.
    """

    # document_parsing
    document_parsing_max_concurrent: int = Field(default=10, ge=1, description="Maximum number of concurrent document parsing tasks per worker.")  # fmt: off

    # general
    disabled_routers: list[RouterName] = Field(default_factory=list, description="Disabled routers to limits services of the API.", examples=[["embeddings"]], json_schema_extra={"default": []})  # fmt: off
    hidden_routers: list[RouterName] = Field(default_factory=list, description="Routers are enabled but hidden in the swagger and the documentation of the API.", examples=[["admin"]], json_schema_extra={"default": []})  # fmt: off
    app_title: str = Field(default=DEFAULT_APP_NAME, description="Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API"])  # fmt: off

    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Logging level of the API.")  # fmt: off
    log_format: str = Field(default="[%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s", description="Logging format of the API.")  # fmt: off

    # monitoring
    monitoring_prometheus_enabled: bool = Field(default=True, description="If true, Prometheus metrics will be exposed in the `/metrics` endpoint.")  # fmt: off

    # usage tokenizer
    usage_tokenizer: Tokenizer = Field(default=Tokenizer.TIKTOKEN_GPT2, description="Tokenizer used to compute usage of the API.")

    # swagger
    swagger_summary: str = Field(default="You can configuration this swagger UI in the configuration file, like hide routes or change the title.", description="Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API description."])  # fmt: off
    swagger_version: str = Field(default="latest", description="Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["2.5.0"])  # fmt: off
    swagger_description: str = Field(default="[See documentation](https://github.com/etalab-ia/opengaterag/blob/main/README.md)", description="Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["[See documentation](https://github.com/etalab-ia/opengaterag/blob/main/README.md)"])  # fmt: off
    swagger_contact: dict | None = Field(default=None, description="Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_license_info: dict = Field(default={"name": "MIT Licence", "identifier": "MIT", "url": "https://raw.githubusercontent.com/etalab-ia/opengaterag/refs/heads/main/LICENSE"}, description="Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_terms_of_service: str | None = Field(default=None, description="A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL.", examples=["https://example.com/terms-of-service"])  # fmt: off
    swagger_openapi_tags: list[dict[str, str | dict[str, str]]] = Field(default_factory=list, description="OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", json_schema_extra={"default": []})  # fmt: off
    swagger_openapi_url: str = Field(default="/openapi.json", pattern=r"^/", description="OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_docs_url: str = Field(default="/docs", pattern=r"^/", description="Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_redoc_url: str = Field(default="/redoc", pattern=r"^/", description="Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off


# load config ----------------------------------------------------------------------------------------------------------------------------------------
@custom_validation_error()
class ConfigFile(ConfigBaseModel):
    """
    Configuration file is composed of 3 sections, models:
    - `models`: to declare models API exposed to the API.
    - `dependencies`: to declare both required plugins for the API (e.g. PostgreSQL, Redis) and optional ones (e.g. Elasticsearch).
    - `settings`: to configure the API.

    :::warnings
    We don't recommend to use the configuration file to declare models, prefer to use the API to declare models, by endpoints or on the Playground UI (see [Models configuration](/getting-started/models/)).
    :::
    """

    dependencies: Dependencies = Field(default_factory=Dependencies, description="Dependencies used by the API.")  # fmt: off
    settings: Settings = Field(default_factory=Settings, description="General settings configuration fields.")  # fmt: off

    @field_validator("settings", mode="before")
    def set_default_settings(cls, settings) -> Any:
        if settings is None:
            return Settings()
        return settings


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    # config
    config_file: str = "config.yml"
    prometheus_multiproc_dir: str = "/tmp/prometheus_multiproc"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert Path(config_file).is_file(), f"Config file ({config_file}) not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(self) -> Any:
        with open(file=self.config_file) as file:
            lines = file.readlines()

        # remove commented lines
        uncommented_lines = [line for line in lines if not line.lstrip().startswith("#")]

        # replace environment variables
        file_content = self.replace_environment_variables(file_content="".join(uncommented_lines))
        # load config
        config = ConfigFile(**yaml.safe_load(stream=file_content))

        self.dependencies = config.dependencies
        self.settings = config.settings

        return self

    @classmethod
    def replace_environment_variables(cls, file_content):
        env_variable_pattern = re.compile(r"\${([A-Z0-9_]+)(:-[^}]*)?}")

        def replace_env_var(match):
            env_variable_definition = match.group(0)
            env_variable_name = match.group(1)
            default_env_variable_value = match.group(2)[2:] if match.group(2) else None

            env_variable_value = os.getenv(env_variable_name)

            if env_variable_value is not None and env_variable_value != "":
                return env_variable_value
            elif default_env_variable_value is not None:
                return default_env_variable_value
            else:
                logging.warning(f"Environment variable {env_variable_name} not found or empty to replace {env_variable_definition}.")
                return env_variable_definition

        file_content = env_variable_pattern.sub(replace_env_var, file_content)

        return file_content


@lru_cache
def get_configuration() -> Configuration:
    return Configuration()


configuration = get_configuration()
