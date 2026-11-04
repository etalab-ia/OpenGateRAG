from io import BytesIO
from pathlib import Path
import zipfile

from docx import Document as DocxDocument
from odfdo import Document as OdfDocument
from odfdo import DrawPage, Frame, Header, Paragraph, Table
from openpyxl import Workbook
from pptx import Presentation

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
ODT_MIME = "application/vnd.oasis.opendocument.text"
ODS_MIME = "application/vnd.oasis.opendocument.spreadsheet"
ODP_MIME = "application/vnd.oasis.opendocument.presentation"
EPUB_MIME = "application/epub+zip"


def build_docx(_: Path) -> bytes:
    document = DocxDocument()
    document.add_heading("DOCX milestone", level=1)
    document.add_paragraph("A paragraph from the DOCX fixture.")
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def build_xlsx(_: Path) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"] = "XLSX milestone"
    sheet["B1"] = 42
    workbook.create_sheet("Second sheet")["A1"] = "Second worksheet content"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def build_pptx(_: Path) -> bytes:
    presentation = Presentation()
    first = presentation.slides.add_slide(presentation.slide_layouts[1])
    first.shapes.title.text = "First slide marker"
    first.placeholders[1].text = "First slide body"
    second = presentation.slides.add_slide(presentation.slide_layouts[1])
    second.shapes.title.text = "Second slide marker"
    second.placeholders[1].text = "Second slide body"
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()


def build_odt(path: Path) -> bytes:
    document = OdfDocument("text")
    document.body.clear()
    document.body.append(Header(1, "ODT milestone"))
    document.body.append(Paragraph("A paragraph from the ODT fixture."))
    document.save(str(path))
    return path.read_bytes()


def build_ods(path: Path) -> bytes:
    document = OdfDocument("spreadsheet")
    document.body.clear()
    sheet = Table("Sheet1", width=2, height=2)
    sheet.set_value("A1", "ODS milestone")
    sheet.set_value("B1", 42)
    document.body.append(sheet)
    document.save(str(path))
    return path.read_bytes()


def build_odp(path: Path) -> bytes:
    document = OdfDocument("presentation")
    document.body.clear()
    slide = DrawPage("page1", name="Slide One")
    slide.append(Frame.text_frame(["ODP slide marker"], size=("10cm", "2cm"), position=("1cm", "1cm")))
    document.body.append(slide)
    document.save(str(path))
    return path.read_bytes()


def build_csv(_: Path) -> bytes:
    return b"name,value\nCSV milestone,42\n"


def build_epub(path: Path) -> bytes:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as epub:
        epub.writestr("mimetype", EPUB_MIME, compress_type=zipfile.ZIP_STORED)
        epub.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""",
        )
        epub.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">fixture-book</dc:identifier>
    <dc:title>EPUB fixture</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
  <spine><itemref idref="chapter"/></spine>
</package>""",
        )
        epub.writestr(
            "OEBPS/chapter.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>EPUB fixture</title></head>
  <body><h1>EPUB chapter marker</h1><p>A paragraph from the EPUB fixture.</p></body>
</html>""",
        )
    return path.read_bytes()
