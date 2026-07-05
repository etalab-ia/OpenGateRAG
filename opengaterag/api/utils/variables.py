from enum import StrEnum

DEFAULT_APP_NAME = "opengaterag"


class RouterName(StrEnum):
    COLLECTIONS = ("collections", "opengaterag.api.endpoints.collections")
    DOCUMENTS = ("documents", "opengaterag.api.endpoints.documents")
    MONITORING = ("monitoring", None)
    SEARCH = ("search", "opengaterag.api.endpoints.search")

    def __new__(cls, value: str, module_path: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.module_path = module_path

        return obj


class EndpointRoute(StrEnum):
    COLLECTIONS = f"/{RouterName.COLLECTIONS}"
    DOCUMENTS = f"/{RouterName.DOCUMENTS}"
    METRICS = "/metrics"
    SEARCH = f"/{RouterName.SEARCH}"
