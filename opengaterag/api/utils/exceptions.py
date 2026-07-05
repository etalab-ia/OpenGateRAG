from fastapi import HTTPException


# 400
class InsufficientStorageLimitException(HTTPException):
    def __init__(self, detail: str = "Insufficient upload tokens limit.") -> None:
        super().__init__(status_code=400, detail=detail)


class WrongSearchMethodException(HTTPException):
    def __init__(self, detail: str = "Wrong search method.") -> None:
        super().__init__(status_code=400, detail=detail)


# 403
class InvalidAuthenticationSchemeException(HTTPException):
    def __init__(self, detail: str = "Invalid authentication scheme.") -> None:
        super().__init__(status_code=403, detail=detail)


class InvalidAPIKeyException(HTTPException):
    def __init__(self, detail: str = "Invalid API key.") -> None:
        super().__init__(status_code=403, detail=detail)


# 404
class ChunkNotFoundException(HTTPException):
    def __init__(self, detail: str = "Chunk not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class CollectionNotFoundException(HTTPException):
    def __init__(self, detail: str = "Collection not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class DocumentNotFoundException(HTTPException):
    def __init__(self, detail: str = "Document not found.") -> None:
        super().__init__(status_code=404, detail=detail)


# 413
class FileSizeLimitExceededException(HTTPException):
    MAX_CONTENT_SIZE = 20_000_000  # 20MB

    def __init__(self, detail: str = f"File size limit exceeded (max: {MAX_CONTENT_SIZE} bytes).") -> None:
        super().__init__(status_code=413, detail=detail)


# 422
class UnsupportedFileTypeException(HTTPException):
    def __init__(self, detail: str = "Unsupported file type.") -> None:
        super().__init__(status_code=422, detail=detail)


# 500
class ChunkingFailedException(HTTPException):
    def __init__(self, detail: str = "Chunking failed.") -> None:
        super().__init__(status_code=500, detail=detail)


class ParsingDocumentFailedException(HTTPException):
    def __init__(self, detail: str = "Parsing document failed.") -> None:
        super().__init__(status_code=500, detail=detail)


class VectorizationFailedException(HTTPException):
    def __init__(self, detail: str = "Vectorization failed.") -> None:
        super().__init__(status_code=500, detail=detail)
