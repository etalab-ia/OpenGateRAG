import asyncio
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
import logging
from pathlib import Path
import zipfile

from docling.datamodel.backend_options import (
    CsvBackendOptions,
    DeclarativeBackendOptions,
    EpubBackendOptions,
    MsExcelBackendOptions,
    MsPowerpointBackendOptions,
    MsWordBackendOptions,
    OdsBackendOptions,
)
from docling.datamodel.base_models import ConversionStatus, DocumentStream, InputFormat
from docling.document_converter import (
    CsvFormatOption,
    DocumentConverter,
    EpubFormatOption,
    ExcelFormatOption,
    OdpFormatOption,
    OdsFormatOption,
    OdtFormatOption,
    PowerpointFormatOption,
    WordFormatOption,
)
from fastapi import UploadFile
from html_to_markdown import convert_to_markdown
import pymupdf
import pymupdf4llm

from opengaterag.api.utils.exceptions import UnsupportedFileTypeException

logger = logging.getLogger(__name__)


class FileType(StrEnum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MD = "md"
    TXT = "txt"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    ODT = "odt"
    ODS = "ods"
    ODP = "odp"
    CSV = "csv"
    EPUB = "epub"


@dataclass(frozen=True)
class ParserArchiveLimits:
    max_file_bytes: int = 128 * 1024 * 1024
    max_total_bytes: int = 512 * 1024 * 1024
    max_member_count: int = 10_000


class ParserManager:
    EXTENSION_MAP: dict[str, FileType] = {
        ".pdf": FileType.PDF,
        ".html": FileType.HTML,
        ".htm": FileType.HTML,
        ".md": FileType.MD,
        ".markdown": FileType.MD,
        ".txt": FileType.TXT,
        ".text": FileType.TXT,
        ".docx": FileType.DOCX,
        ".xlsx": FileType.XLSX,
        ".pptx": FileType.PPTX,
        ".odt": FileType.ODT,
        ".ods": FileType.ODS,
        ".odp": FileType.ODP,
        ".csv": FileType.CSV,
        ".epub": FileType.EPUB,
    }

    VALID_CONTENT_TYPES: dict[FileType, set[str]] = {
        FileType.PDF: {
            "application/pdf",
            "application/octet-stream",
        },
        FileType.HTML: {
            "text/html",
            "text/plain",
            "application/html",
            "application/octet-stream",
        },
        FileType.MD: {
            "text/markdown",
            "text/x-markdown",
            "text/plain",
            "application/markdown",
            "application/octet-stream",
        },
        FileType.TXT: {
            "text/plain",
            "text/txt",
            "application/octet-stream",
        },
        FileType.DOCX: {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
        FileType.XLSX: {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        },
        FileType.PPTX: {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/octet-stream",
        },
        FileType.ODT: {
            "application/vnd.oasis.opendocument.text",
            "application/octet-stream",
        },
        FileType.ODS: {
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/octet-stream",
        },
        FileType.ODP: {
            "application/vnd.oasis.opendocument.presentation",
            "application/octet-stream",
        },
        FileType.CSV: {
            "text/csv",
            "application/csv",
            "text/plain",
            "application/octet-stream",
        },
        FileType.EPUB: {
            "application/epub+zip",
            "application/octet-stream",
        },
    }

    DOCLING_FORMATS: dict[FileType, InputFormat] = {
        FileType.DOCX: InputFormat.DOCX,
        FileType.XLSX: InputFormat.XLSX,
        FileType.PPTX: InputFormat.PPTX,
        FileType.ODT: InputFormat.ODT,
        FileType.ODS: InputFormat.ODS,
        FileType.ODP: InputFormat.ODP,
        FileType.CSV: InputFormat.CSV,
        FileType.EPUB: InputFormat.EPUB,
    }
    ARCHIVE_FILE_TYPES = {
        FileType.DOCX,
        FileType.XLSX,
        FileType.PPTX,
        FileType.ODT,
        FileType.ODS,
        FileType.ODP,
        FileType.EPUB,
    }

    def __init__(self, max_concurrent: int = 10, archive_limits: ParserArchiveLimits | None = None):
        self.conversion_semaphore = asyncio.Semaphore(value=max_concurrent)
        self.archive_limits = archive_limits or ParserArchiveLimits()

    async def parse(self, file: UploadFile, pages: list[int] | None = None) -> str | list[dict]:
        file_type = self.check_file_type(file=file)
        content = None

        match file_type:
            case FileType.PDF:
                async with self.conversion_semaphore:
                    file_content = await file.read()
                    with pymupdf.open(stream=file_content, filetype="pdf") as doc:
                        content = await asyncio.to_thread(pymupdf4llm.to_markdown, doc, pages=pages, page_chunks=True)

            case FileType.HTML:
                file_content = await self._read_content(file=file)
                content = convert_to_markdown(file_content).strip()

            case FileType.MD:
                file_content = await self._read_content(file=file)
                content = file_content.strip()

            case FileType.TXT:
                file_content = await self._read_content(file=file)
                content = file_content.strip()

            case _ if file_type in self.DOCLING_FORMATS:
                async with self.conversion_semaphore:
                    file_content = await file.read()
                    filename = Path(file.filename or f"document.{file_type.value}").name
                    content = await asyncio.to_thread(self._parse_with_docling, file_content, filename, file_type)

        return content

    def _parse_with_docling(self, content: bytes, filename: str, file_type: FileType) -> str | list[dict]:
        if file_type in self.ARCHIVE_FILE_TYPES:
            self._check_archive_limits(content)

        input_format = self.DOCLING_FORMATS[file_type]
        no_fetch = {"enable_local_fetch": False, "enable_remote_fetch": False}
        archive_options = {
            **no_fetch,
            "max_file_bytes": self.archive_limits.max_file_bytes,
            "max_total_bytes": self.archive_limits.max_total_bytes,
            "max_member_count": self.archive_limits.max_member_count,
        }

        match file_type:
            case FileType.DOCX:
                format_option = WordFormatOption(backend_options=MsWordBackendOptions(**archive_options))
            case FileType.XLSX:
                format_option = ExcelFormatOption(backend_options=MsExcelBackendOptions(**archive_options))
            case FileType.PPTX:
                format_option = PowerpointFormatOption(backend_options=MsPowerpointBackendOptions(**no_fetch, render_chart_images=False))
            case FileType.ODT:
                format_option = OdtFormatOption(backend_options=DeclarativeBackendOptions(**no_fetch))
            case FileType.ODS:
                format_option = OdsFormatOption(backend_options=OdsBackendOptions(**no_fetch))
            case FileType.ODP:
                format_option = OdpFormatOption(backend_options=DeclarativeBackendOptions(**no_fetch))
            case FileType.CSV:
                format_option = CsvFormatOption(backend_options=CsvBackendOptions(**no_fetch))
            case FileType.EPUB:
                format_option = EpubFormatOption(backend_options=EpubBackendOptions(**archive_options, fetch_images=False))
            case _:
                raise UnsupportedFileTypeException()

        converter = DocumentConverter(
            allowed_formats=[input_format],
            format_options={input_format: format_option},
        )
        result = converter.convert(
            DocumentStream(name=filename, stream=BytesIO(content)),
            raises_on_error=False,
        )
        if result.status != ConversionStatus.SUCCESS or result.document is None:
            logger.debug("Docling rejected %s: %s", filename, result.errors)
            raise ValueError("Document conversion failed or produced partial output")

        if file_type == FileType.PPTX:
            return [
                {"text": text, "metadata": {"page": page_number}}
                for page_number in sorted(result.document.pages)
                if (text := result.document.export_to_markdown(page_no=page_number).strip())
            ]

        return result.document.export_to_markdown().strip()

    def _check_archive_limits(self, content: bytes) -> None:
        limits = self.archive_limits
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                members = archive.infolist()
                if len(members) > limits.max_member_count:
                    raise ValueError("Archive has too many members")
                if sum(member.file_size for member in members) > limits.max_total_bytes:
                    raise ValueError("Archive exceeds the total decompressed-size limit")

                total_size = 0
                for member in members:
                    if member.file_size > limits.max_file_bytes:
                        raise ValueError("Archive member exceeds the decompressed-size limit")
                    member_size = 0
                    with archive.open(member) as stream:
                        while chunk := stream.read(min(1024 * 1024, limits.max_file_bytes - member_size + 1)):
                            member_size += len(chunk)
                            total_size += len(chunk)
                            if member_size > limits.max_file_bytes:
                                raise ValueError("Archive member exceeds the decompressed-size limit")
                            if total_size > limits.max_total_bytes:
                                raise ValueError("Archive exceeds the total decompressed-size limit")
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as e:
            raise ValueError("Invalid or unsupported archive document") from e

    def check_file_type(self, file: UploadFile, type: FileType | None = None) -> FileType:
        """
        Detect file type by extension, then check content-type.
        """
        try:
            filename = file.filename or ""
            extension = Path(filename).suffix.lower()
            content_type = file.content_type or ""
        except Exception:
            raise UnsupportedFileTypeException()

        # detect type by extension and content-type
        detected_type = None
        if extension in self.EXTENSION_MAP:
            file_type = self.EXTENSION_MAP[extension]
            if content_type in self.VALID_CONTENT_TYPES[file_type]:
                detected_type = file_type
        else:
            # detect type only by content-type (less robust because it stops after first match)
            for file_type, valid_content_types in self.VALID_CONTENT_TYPES.items():
                if content_type in valid_content_types and content_type != "application/octet-stream":
                    detected_type = file_type

        if detected_type is None:
            logger.debug(f"Failed to detect file type: extension={extension}, content_type={content_type}")
            raise UnsupportedFileTypeException()

        if type is not None and detected_type != type:
            raise UnsupportedFileTypeException(f"File must be a {type.value} file.")

        return detected_type

    @staticmethod
    async def _read_content(file: UploadFile) -> str:
        content_bytes = await file.read()
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content_bytes.decode("latin-1")
            except UnicodeDecodeError as e:
                logger.debug(msg=f"Encoding problem detected for {file.filename}: {e}")
                content = content_bytes.decode("utf-8", errors="replace")

        await file.seek(0)

        return content
