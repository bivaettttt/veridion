from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePath
import re
import unicodedata
from xml.etree import ElementTree
from zipfile import ZipFile

from markdown_it import MarkdownIt
from pypdf import PdfReader

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 180_000
MEDIA = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class Part:
    text: str
    heading: str = "Document"
    page: int | None = None


class VisibleHTML(HTMLParser):
    excluded = {"script", "style", "template", "iframe", "object", "noscript"}
    headings = {"h1", "h2", "h3", "h4", "h5", "h6"}
    blocks = headings | {"p", "li", "section", "article", "div", "br", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[Part] = []
        self.buffer: list[str] = []
        self.heading = "Document"
        self.hidden: list[str] = []

    def flush(self, heading: bool = False) -> None:
        value = "".join(self.buffer).strip()
        self.buffer.clear()
        if value:
            if heading:
                self.heading = value[:150]
            self.parts.append(Part(value, self.heading))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.excluded:
            self.hidden.append(tag)
        elif not self.hidden and tag in self.blocks:
            self.flush()

    def handle_endtag(self, tag: str) -> None:
        if self.hidden:
            if self.hidden[-1] == tag:
                self.hidden.pop()
        elif tag in self.blocks:
            self.flush(tag in self.headings)

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.buffer.append(data)


def parse(filename: str, payload: bytes) -> tuple[str, list[Part]]:
    suffix = PurePath(filename).suffix.lower()
    if suffix not in MEDIA or not 0 < len(payload) <= MAX_BYTES:
        raise ValueError("Unsupported file type or size")
    if suffix == ".pdf":
        reader = PdfReader(BytesIO(payload), strict=True)
        if reader.is_encrypted or len(reader.pages) > 80:
            raise ValueError("Encrypted PDF or too many pages")
        parts = [
            Part(page.extract_text(), f"Page {index}", index)
            for index, page in enumerate(reader.pages, 1)
        ]
    elif suffix == ".docx":
        with ZipFile(BytesIO(payload)) as archive:
            info = archive.infolist()
            if (
                len(info) > 250
                or sum(entry.file_size for entry in info) > 16 * MAX_BYTES
            ):
                raise ValueError("DOCX archive exceeds limits")
            xml = archive.read("word/document.xml")
        if len(xml) > MAX_BYTES or re.search(rb"<!\s*(ENTITY|DOCTYPE)", xml, re.I):
            raise ValueError("Unsupported DOCX XML")
        root = ElementTree.fromstring(xml)
        parts = []
        heading = "Document"
        for paragraph in root.iter(f"{W}p"):
            value = "".join(node.text or "" for node in paragraph.iter(f"{W}t"))
            style = paragraph.find(f"{W}pPr/{W}pStyle")
            if style is not None and style.attrib.get(f"{W}val", "").startswith(
                "Heading"
            ):
                heading = value[:150]
            parts.append(Part(value, heading))
    elif suffix in {".md", ".html"}:
        data = payload.decode("utf-8-sig")
        if suffix == ".md":
            data = MarkdownIt("commonmark", {"html": False}).render(data)
        parser = VisibleHTML()
        parser.feed(data)
        parser.close()
        parser.flush()
        parts = parser.parts
    else:
        parts = [Part(payload.decode("utf-8-sig"))]

    normalized = []
    for part in parts:
        value = unicodedata.normalize("NFC", part.text.replace("\x00", ""))
        value = "\n".join(" ".join(line.split()) for line in value.splitlines()).strip()
        if value:
            normalized.append(Part(value, part.heading, part.page))
    if not normalized or sum(len(part.text) + 2 for part in normalized) > MAX_TEXT:
        raise ValueError("Missing text layer or normalized text exceeds limits")
    return MEDIA[suffix], normalized


def windows(text: str, size: int = 780, overlap: int = 110):
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary != -1:
                end = boundary
        yield start, end
        if end == len(text):
            return
        next_start = text.find(" ", end - overlap, end)
        start = next_start + 1 if next_start != -1 else end - overlap
