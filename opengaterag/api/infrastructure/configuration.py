from enum import StrEnum
from functools import lru_cache
import logging
import os
from pathlib import Path
import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from pydantic_settings import BaseSettings
import yaml

from opengaterag.api.infrastructure.fastapi.routes import RouterName

DEFAULT_APP_NAME = "OpenGateRAG"


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class OpengateLLMDependency(ConfigBaseModel):
    """
    OpengateLLM is a required dependency of OpenGateLLM. It is used to connect to the OpengateLLM API.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(..., description="URL of the OpengateLLM API.", examples=["https://opengatellm.com"])  # fmt: off
    model_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(..., description="Model of the vector store to be used to embed the text in the vector store.", examples=["text-embedding-3-small"])  # fmt: off
    model_vector_size: Annotated[int, Field(ge=1, description="Size of the vector to be used to embed the text in the vector store.", examples=[1536])]  # fmt: off
    public_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="Public URL of the OpengateLLM API to run swagger UI without CORS issues. If not provided, the public URL will be the same as the `url`.")  # fmt: off
    openapi_url: Annotated[str, Field(default="/openapi.json", description="Path, relative to `url`, where OpengateLLM exposes its OpenAPI schema. Used to build the unified API documentation.", examples=["/openapi.json"])]  # fmt: off


class PostgresDependency(ConfigBaseModel):
    """
    Postgres is a required dependency of OpenGateRAG. In this section, you can pass all postgres python SDK arguments, see https://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-apihttps://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-api for more information.
    Only the `url` argument is required. The connection URL must use the asynchronous scheme, `postgresql+asyncpg://`. If you provide a standard `postgresql://` URL, it will be automatically converted to use asyncpg.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^postgresql\+asyncpg://")] = Field(..., description="PostgreSQL connection url.", examples=["postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"])  # fmt: off


class SentryDependency(ConfigBaseModel):
    """
    Sentry is an optional dependency of OpenGateLLM. Sentry helps you identify, diagnose, and fix errors in real-time.
    In this section, you can pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information.
    """

    pass
    # All args of pydantic sentry client is allowed


class Dependencies(ConfigBaseModel):
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


class Settings(ConfigBaseModel):
    """
    General settings configuration fields.
    """

    # storage
    storage_default_limit: int | None = Field(default=10_000_000, ge=0, description="Default storage limit in tokens assigned to newly created users. If null, new users have no storage limit.")  # fmt: off
    storage_compute_tokenizer: Tokenizer = Field(default=Tokenizer.TIKTOKEN_GPT2, description="Tokenizer used to compute storage usage of the API.")

    # general
    disabled_routers: list[RouterName] = Field(default_factory=list, description="Disabled routers to limits services of the API.", examples=[["embeddings"]], json_schema_extra={"default": []})  # fmt: off
    hidden_routers: list[RouterName] = Field(default_factory=list, description="Routers are enabled but hidden in the swagger and the documentation of the API.", examples=[["admin"]], json_schema_extra={"default": []})  # fmt: off
    app_title: str = Field(default=DEFAULT_APP_NAME, description="Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API"])  # fmt: off

    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Logging level of the API.")  # fmt: off
    log_format: str = Field(default="[%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s", description="Logging format of the API.")  # fmt: off

    # monitoring
    monitoring_prometheus_enabled: bool = Field(default=True, description="If true, Prometheus metrics will be exposed in the `/metrics` endpoint.")  # fmt: off

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
class ConfigFile(ConfigBaseModel):
    """
    Configuration file is composed of 2 sections:
    - `dependencies`: to declare both required plugins for the API (e.g. PostgreSQL) and optional ones (e.g. Sentry).
    - `settings`: to configure the API.
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
