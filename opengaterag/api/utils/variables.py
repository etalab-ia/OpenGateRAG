from enum import StrEnum

DEFAULT_APP_NAME = "OpenGateRAG"


class RouterName(StrEnum):
    MONITORING = ("monitoring", None)

    def __new__(cls, value: str, module_path: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.module_path = module_path

        return obj


class EndpointRoute(StrEnum):
    METRICS = "/metrics"
