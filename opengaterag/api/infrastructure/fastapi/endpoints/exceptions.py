from fastapi import HTTPException


# 401
class InvalidAPIKeyHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid API key."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


# 403
class PublicCollectionNotAllowedHTTPException(HTTPException):
    status_code = 403
    detail = "You are not allowed to make a collection public."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


# 404
class CollectionNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Collection not found."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)
