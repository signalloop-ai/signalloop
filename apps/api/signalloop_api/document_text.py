from __future__ import annotations

import html
import re
import zlib
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


class DocumentTextExtractionError(ValueError):
    pass


def extract_document_text(filename: str, data: bytes) -> str:
    ext = Path(filename.lower()).suffix
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentTextExtractionError("Upload a .txt, .md, .pdf, or .docx file.")
    if ext in {".txt", ".md"}:
        return _normalize_text(_decode_text(data))
    if ext == ".docx":
        return _extract_docx_text(data)
    return _extract_pdf_text(data)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentTextExtractionError("Could not decode text from this file.")


def _extract_docx_text(data: bytes) -> str:
    try:
        with ZipFile(BytesIO(data)) as docx:
            xml = docx.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise DocumentTextExtractionError("Could not read DOCX text from this file.") from exc

    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise DocumentTextExtractionError("Could not parse DOCX text from this file.") from exc

    paragraphs: list[str] = []
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for paragraph in root.findall(".//w:p", namespace):
        parts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return _normalize_text("\n".join(paragraphs))


def _extract_pdf_text(data: bytes) -> str:
    streams = _pdf_stream_payloads(data)
    chunks: list[str] = []
    for stream in streams:
        chunks.extend(_pdf_text_tokens(stream))
    text = _normalize_text("\n".join(chunks))
    if len(text) < 20:
        raise DocumentTextExtractionError(
            "Could not extract usable text from this PDF. Scanned or encoded PDFs are not supported yet; paste the text or upload DOCX/TXT."
        )
    return text


def _pdf_stream_payloads(data: bytes) -> list[bytes]:
    streams: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, flags=re.DOTALL):
        raw = match.group(1).strip(b"\r\n")
        for payload in (raw, _try_inflate(raw)):
            if payload:
                streams.append(payload)
    if not streams:
        streams.append(data)
    return streams


def _try_inflate(data: bytes) -> bytes | None:
    try:
        return zlib.decompress(data)
    except zlib.error:
        return None


def _pdf_text_tokens(data: bytes) -> list[str]:
    text = data.decode("latin-1", errors="ignore")
    tokens: list[str] = []
    for match in re.finditer(r"\(((?:\\.|[^\\)])*)\)\s*Tj", text):
        tokens.append(_unescape_pdf_string(match.group(1)))
    for array in re.finditer(r"\[((?:\s*\((?:\\.|[^\\)])*\)\s*-?\d*)+)\]\s*TJ", text):
        tokens.extend(_unescape_pdf_string(item) for item in re.findall(r"\(((?:\\.|[^\\)])*)\)", array.group(1)))
    return tokens


def _unescape_pdf_string(value: str) -> str:
    value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    value = re.sub(r"\\([nrtbf])", " ", value)
    value = re.sub(r"\\[0-7]{1,3}", " ", value)
    return html.unescape(value)


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line).strip()
