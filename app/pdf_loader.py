from pathlib import Path
from docling.document_converter import DocumentConverter

def load_pdf_text(pdf_path: Path) -> str:
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    if hasattr(doc, "export_to_markdown"):
        return doc.export_to_markdown()
    return doc.export_to_text()


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[tuple[str, int]]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_newline = chunk.rfind("\n")
            if last_newline > chunk_size // 2:
                end = start + last_newline + 1
                chunk = text[start:end]

        if chunk.strip():
            chunks.append((chunk.strip(), start))

        start = end - overlap if end < len(text) else len(text)

    return chunks
