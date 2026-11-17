from io import BytesIO

from fastapi import UploadFile
import pytest
from starlette.datastructures import Headers

from opengaterag.api.helpers._parsermanager import FileType, ParserManager
from opengaterag.api.utils.exceptions import UnsupportedFileTypeException


def create_upload_file(content: str, filename: str, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content.encode("utf-8")), headers=Headers({"content-type": content_type}))


class TestCheckFileType:
    @pytest.mark.parametrize(
        "filename,content_type,expected",
        [
            ("test.txt", "text/plain", FileType.TXT),
            ("test.txt", "text/plain; charset=utf-8", FileType.TXT),
            ("test.txt", "Text/Plain; Charset=UTF-8", FileType.TXT),
            ("test.md", "text/markdown;charset=utf-8", FileType.MD),
            ("test.html", "text/html; charset=iso-8859-1", FileType.HTML),
            ("test.pdf", "application/pdf; name=test.pdf", FileType.PDF),
        ],
    )
    def test_check_file_type_ignores_content_type_parameters(self, filename, content_type, expected):
        """Test that parameters such as charset in the Content-Type header are ignored (regression test for #11)."""
        file = create_upload_file("Test content", filename, content_type)

        assert ParserManager().check_file_type(file=file) == expected

    def test_check_file_type_without_extension_ignores_content_type_parameters(self):
        """Test that detection by content-type only also ignores parameters."""
        file = create_upload_file("Test content", "test", "text/markdown; charset=utf-8")

        assert ParserManager().check_file_type(file=file) == FileType.MD

    def test_check_file_type_unsupported_content_type_with_parameters(self):
        """Test that an unsupported content-type is still rejected when it has parameters."""
        file = create_upload_file("Test content", "test.txt", "image/png; charset=utf-8")

        with pytest.raises(UnsupportedFileTypeException):
            ParserManager().check_file_type(file=file)


class TestParse:
    @pytest.mark.asyncio
    async def test_parse_text_file_with_charset(self):
        """Test that a text file sent with a charset parameter is parsed."""
        file = create_upload_file("  Bonjour, ceci est un test.  ", "test.txt", "text/plain; charset=utf-8")

        content = await ParserManager().parse(file=file)

        assert content == "Bonjour, ceci est un test."
