from io import BytesIO
import socket
import zipfile

from fastapi import UploadFile
import pytest
from starlette.datastructures import Headers

from opengaterag.api.helpers._parsermanager import ParserArchiveLimits, ParserManager
from opengaterag.api.tests.document_fixtures import (
    DOCX_MIME,
    EPUB_MIME,
    ODP_MIME,
    ODS_MIME,
    ODT_MIME,
    PPTX_MIME,
    XLSX_MIME,
    build_csv,
    build_docx,
    build_epub,
    build_odp,
    build_ods,
    build_odt,
    build_pptx,
    build_xlsx,
)


def make_upload(content: bytes, filename: str, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content), headers=Headers({"content-type": content_type}))


@pytest.mark.parametrize(
    ("filename", "content_type", "builder", "expected"),
    [
        pytest.param("sample.docx", DOCX_MIME, build_docx, "DOCX milestone", id="docx"),
        pytest.param("sample.xlsx", XLSX_MIME, build_xlsx, "XLSX milestone", id="xlsx"),
        pytest.param("sample.pptx", PPTX_MIME, build_pptx, "First slide marker", id="pptx"),
        pytest.param("sample.odt", ODT_MIME, build_odt, "ODT milestone", id="odt"),
        pytest.param("sample.ods", ODS_MIME, build_ods, "ODS milestone", id="ods"),
        pytest.param("sample.odp", ODP_MIME, build_odp, "ODP slide marker", id="odp"),
        pytest.param("sample.csv", "text/csv", build_csv, "CSV milestone", id="csv"),
        pytest.param("sample.epub", EPUB_MIME, build_epub, "EPUB chapter marker", id="epub"),
    ],
)
@pytest.mark.asyncio
async def test_docling_formats_extract_without_network(filename, content_type, builder, expected, tmp_path, monkeypatch):
    def reject_network(*args, **kwargs):
        raise AssertionError("Document conversion attempted outbound network access")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket, "getaddrinfo", reject_network)
    monkeypatch.setattr(socket.socket, "connect", reject_network)

    parsed = await ParserManager().parse(make_upload(builder(tmp_path / filename), filename, content_type))

    if filename.endswith(".pptx"):
        assert isinstance(parsed, list)
        combined_text = "\n".join(page["text"] for page in parsed)
    else:
        assert isinstance(parsed, str)
        combined_text = parsed
    assert expected in combined_text


@pytest.mark.asyncio
async def test_pptx_pages_preserve_slide_numbers(tmp_path):
    parsed = await ParserManager().parse(make_upload(build_pptx(tmp_path / "slides.pptx"), "slides.pptx", PPTX_MIME))

    assert isinstance(parsed, list)
    assert [page["metadata"] for page in parsed] == [{"page": 1}, {"page": 2}]
    assert "First slide marker" in parsed[0]["text"]
    assert "Second slide marker" in parsed[1]["text"]


@pytest.mark.asyncio
async def test_docling_rejects_content_that_does_not_match_the_allowed_format(tmp_path):
    docx_content = build_docx(tmp_path / "actually.docx")

    with pytest.raises(ValueError, match="conversion failed"):
        await ParserManager().parse(make_upload(docx_content, "mislabeled.xlsx", XLSX_MIME))


@pytest.mark.asyncio
async def test_malformed_archive_is_rejected():
    with pytest.raises(ValueError, match="Invalid or unsupported archive"):
        await ParserManager().parse(make_upload(b"not a zip archive", "broken.pptx", PPTX_MIME))


@pytest.mark.parametrize(
    ("limits", "expected"),
    [
        pytest.param(ParserArchiveLimits(max_member_count=1), "too many members", id="member-count"),
        pytest.param(ParserArchiveLimits(max_file_bytes=16), "member exceeds", id="member-size"),
        pytest.param(ParserArchiveLimits(max_total_bytes=64), "total decompressed-size", id="total-size"),
    ],
)
@pytest.mark.asyncio
async def test_archive_limits_are_enforced(limits, expected, tmp_path):
    path = tmp_path / "limited.odt"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", ODT_MIME)
        archive.writestr("content.xml", bytes(128))

    with pytest.raises(ValueError, match=expected):
        await ParserManager(archive_limits=limits).parse(make_upload(path.read_bytes(), path.name, ODT_MIME))


@pytest.mark.parametrize("filename", ["README", "notes.data"])
@pytest.mark.asyncio
async def test_plain_text_without_a_recognized_extension_remains_txt(filename):
    content = b"plain text without delimiters\nsecond line\n"

    parsed = await ParserManager().parse(make_upload(content, filename, "text/plain"))

    assert parsed == "plain text without delimiters\nsecond line"


@pytest.mark.asyncio
async def test_single_column_csv_without_an_extension_is_accepted():
    parsed = await ParserManager().parse(make_upload(b"column\nvalue\n", "README", "text/csv"))

    assert "column" in parsed
    assert "value" in parsed


@pytest.mark.asyncio
async def test_epub_requires_every_spine_document_to_be_readable(tmp_path):
    valid = await ParserManager().parse(make_upload(build_epub(tmp_path / "valid.epub"), "valid.epub", EPUB_MIME))
    assert "EPUB chapter marker" in valid
    assert "EPUB second chapter" in valid

    for filename, options in (("invalid.epub", {"invalid_chapter": True}), ("missing.epub", {"missing_chapter": True})):
        with pytest.raises(ValueError, match="Invalid EPUB content document"):
            await ParserManager().parse(make_upload(build_epub(tmp_path / filename, **options), filename, EPUB_MIME))
