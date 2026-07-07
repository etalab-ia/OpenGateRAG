from enum import StrEnum


class PermissionType(StrEnum):
    ADMIN = "admin"
    CREATE_PUBLIC_COLLECTION = "create_public_collection"
    READ_METRIC = "read_metric"
    PROVIDE_MODELS = "provide_models"

    @classmethod
    def can_create_public_collection(cls, user_permissions: list[str]) -> bool:
        return cls.ADMIN in user_permissions or cls.CREATE_PUBLIC_COLLECTION in user_permissions
