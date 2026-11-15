import hashlib
from io import BytesIO
from zipfile import ZipFile

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from veridion.documents import parse, windows
from veridion.grounding import assess, extract


def pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(612, 792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 14 Tf 50 700 Td (Veridion sample) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def docx():
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "word/document.xml",
            """
          <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:body><w:p><w:r><w:t>Veridion sample</w:t></w:r></w:p></w:body>
          </w:document>
        """,
        )
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("a.txt", b"Veridion sample"),
        ("a.md", b"# Veridion sample"),
        ("a.html", b"<h2>Veridion sample</h2><script>Hidden content</script>"),
        ("a.pdf", pdf()),
        ("a.docx", docx()),
    ],
)
def test_formats(filename, payload):
    before = hashlib.sha256(payload).digest()
    _, parts = parse(filename, payload)
    assert [part.text for part in parts] == ["Veridion sample"]
    assert hashlib.sha256(payload).digest() == before
    if filename.endswith(".pdf"):
        assert parts[0].page == 1


def test_chunk_offsets_cover_normalized_unicode_text():
    _, parts = parse("a.txt", ("смысл 🙂 " * 450).encode())
    text = parts[0].text
    spans = list(windows(text))
    assert spans[0][0] == 0 and spans[-1][-1] == len(text)
    assert all(a < b <= c < d for (a, c), (b, d) in zip(spans, spans[1:]))


def test_modalities_and_compound_claims():
    target = {
        "content": "Build 2.0 requires 10 000 concurrent users.",
        "category": "specification",
        "chunk_id": "spec",
    }
    test = {
        "content": "Build 2.0 test observed 2 000 concurrent users.",
        "category": "test",
        "chunk_id": "test",
    }
    res = assess("Does the platform support 10 000 concurrent users?", [test, target])
    assert res["assessment"] == "INSUFFICIENT_EVIDENCE"
    assert res["contradictions"][0]["type"] == "DIFFERENT_MODALITY"
    row = target | {
        "content": "Build 2.0 documents REST and SOAP integration. Build 2.0 plans 99.99% availability."
    }
    assert {fact.value for fact in extract(row)} == {"REST", "SOAP", "99.99"}
