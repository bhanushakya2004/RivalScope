"""Enterprise document parser and vector indexing engine.

Supports CSV, Excel (XLSX, XLS), Word (DOCX), Markdown, Text, and JSON.
Transforms structured and unstructured enterprise documentation into
semantic knowledge chunks with pgvector embeddings for hybrid retrieval.
"""

import csv
import io
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import DocumentHash, InternalDocument, RawDocument
import hashlib

from app.dedup.embedding import compute_deterministic_embedding
from app.dedup.simhash import compute_simhash

logger = get_logger("ingestion.doc_parser")


@dataclass
class ParsedDocument:
    filename: str
    file_type: str
    file_size_bytes: int
    row_count: int | None
    column_names: list[str]
    summary: str
    markdown_preview: str
    chunks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _split_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split clean text into overlapping semantic chunks."""
    if not text:
        return []
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        p_len = len(p_clean)
        if current_len + p_len > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p_clean]
            current_len = p_len
        else:
            current_chunk.append(p_clean)
            current_len += p_len + 2

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks if chunks else [text[:chunk_size]]


def parse_csv(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Parse CSV tabular file with statistics and markdown representation."""
    text_content = file_bytes.decode("utf-8", errors="replace")
    f = io.StringIO(text_content)
    # Detect delimiter
    sample = text_content[:2048]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample)
        delimiter = dialect.delimiter
    except Exception:
        if "\t" in sample:
            delimiter = "\t"
        elif ";" in sample:
            delimiter = ";"

    f.seek(0)
    reader = csv.reader(f, delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return ParsedDocument(
            filename=filename,
            file_type="csv",
            file_size_bytes=len(file_bytes),
            row_count=0,
            column_names=[],
            summary="Empty CSV document",
            markdown_preview="*Empty file*",
            chunks=[],
        )

    header = [h.strip() for h in rows[0]]
    data_rows = rows[1:]
    row_count = len(data_rows)

    # Generate markdown table preview (first 10 rows)
    preview_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in data_rows[:10]:
        padded = (row + [""] * len(header))[: len(header)]
        preview_lines.append("| " + " | ".join([cell.strip() for cell in padded]) + " |")
    markdown_preview = "\n".join(preview_lines)

    summary = (
        f"Tabular CSV document containing {row_count} records across {len(header)} columns: "
        f"{', '.join(header[:8])}{'...' if len(header) > 8 else ''}."
    )

    # Group into text chunks for vector indexing
    chunks = []
    chunk_size = 25
    for i in range(0, len(data_rows), chunk_size):
        batch = data_rows[i : i + chunk_size]
        chunk_lines = [f"# {filename} (Records {i + 1} to {i + len(batch)})"]
        chunk_lines.append("| " + " | ".join(header) + " |")
        chunk_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for r in batch:
            padded = (r + [""] * len(header))[: len(header)]
            chunk_lines.append("| " + " | ".join([c.strip() for c in padded]) + " |")
        chunks.append("\n".join(chunk_lines))

    return ParsedDocument(
        filename=filename,
        file_type="csv",
        file_size_bytes=len(file_bytes),
        row_count=row_count,
        column_names=header,
        summary=summary,
        markdown_preview=markdown_preview,
        chunks=chunks,
    )


def parse_excel(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Parse Excel spreadsheet (.xlsx, .xls) extracting all sheets."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet_names = wb.sheetnames
    all_chunks = []
    total_rows = 0
    all_headers = []
    preview_parts = []

    for sheet_name in sheet_names:
        sheet = wb[sheet_name]
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue

        # Filter empty rows
        non_empty_rows = [r for r in rows if any(cell is not None for cell in r)]
        if not non_empty_rows:
            continue

        raw_header = [str(c).strip() if c is not None else f"Col{idx + 1}" for idx, c in enumerate(non_empty_rows[0])]
        headers = [h for h in raw_header if h]
        data_rows = non_empty_rows[1:]
        sheet_row_count = len(data_rows)
        total_rows += sheet_row_count
        all_headers.extend([f"{sheet_name}.{h}" for h in headers])

        preview_lines = [
            f"### Sheet: {sheet_name} ({sheet_row_count} rows)",
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for r in data_rows[:8]:
            padded = [(str(cell).strip() if cell is not None else "") for cell in (list(r) + [""] * len(headers))[: len(headers)]]
            preview_lines.append("| " + " | ".join(padded) + " |")
        preview_parts.append("\n".join(preview_lines))

        # Chunk sheet data
        chunk_size = 20
        for i in range(0, len(data_rows), chunk_size):
            batch = data_rows[i : i + chunk_size]
            chunk_lines = [f"# {filename} [{sheet_name}] (Records {i + 1} to {i + len(batch)})"]
            chunk_lines.append("| " + " | ".join(headers) + " |")
            chunk_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for r in batch:
                padded = [(str(cell).strip() if cell is not None else "") for cell in (list(r) + [""] * len(headers))[: len(headers)]]
                chunk_lines.append("| " + " | ".join(padded) + " |")
            all_chunks.append("\n".join(chunk_lines))

    summary = (
        f"Excel workbook with {len(sheet_names)} sheet(s) ({', '.join(sheet_names)}) "
        f"and {total_rows} total rows."
    )

    return ParsedDocument(
        filename=filename,
        file_type="xlsx",
        file_size_bytes=len(file_bytes),
        row_count=total_rows,
        column_names=all_headers,
        summary=summary,
        markdown_preview="\n\n".join(preview_parts) if preview_parts else "*Empty workbook*",
        chunks=all_chunks,
        metadata={"sheets": sheet_names},
    )


def parse_docx(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Parse Microsoft Word document (.docx) extracting text and tables."""
    import docx

    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # Extract tables if present
    table_texts = []
    for table in doc.tables:
        table_rows = []
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            if any(cells):
                table_rows.append("| " + " | ".join(cells) + " |")
        if table_rows:
            header_sep = "| " + " | ".join(["---"] * len(table.columns)) + " |"
            if len(table_rows) > 1:
                table_rows.insert(1, header_sep)
            table_texts.append("\n".join(table_rows))

    full_text = "\n\n".join(paragraphs + table_texts)
    chunks = _split_into_chunks(full_text, chunk_size=900)

    summary = (
        f"Word document with {len(paragraphs)} paragraph(s) and {len(doc.tables)} table(s). "
        f"Total word count: ~{sum(len(p.split()) for p in paragraphs)} words."
    )

    preview = "\n\n".join(paragraphs[:6])
    if table_texts:
        preview += "\n\n" + table_texts[0]

    return ParsedDocument(
        filename=filename,
        file_type="docx",
        file_size_bytes=len(file_bytes),
        row_count=len(paragraphs),
        column_names=[],
        summary=summary,
        markdown_preview=preview[:1200] if preview else "*Empty document*",
        chunks=chunks,
    )


def parse_text_or_markdown(file_bytes: bytes, filename: str, ext: str) -> ParsedDocument:
    """Parse Markdown, Plain Text, or JSON documents."""
    text_content = file_bytes.decode("utf-8", errors="replace")

    if ext == "json":
        try:
            parsed_json = json.loads(text_content)
            pretty = json.dumps(parsed_json, indent=2)
            chunks = _split_into_chunks(pretty, chunk_size=1000)
            is_list = isinstance(parsed_json, list)
            item_count = len(parsed_json) if is_list else len(parsed_json.keys())
            summary = f"JSON structure with {item_count} top-level {'items' if is_list else 'keys'}."
            return ParsedDocument(
                filename=filename,
                file_type="json",
                file_size_bytes=len(file_bytes),
                row_count=item_count if is_list else None,
                column_names=list(parsed_json.keys()) if isinstance(parsed_json, dict) else [],
                summary=summary,
                markdown_preview=f"```json\n{pretty[:1000]}\n```",
                chunks=chunks,
            )
        except Exception:
            pass

    chunks = _split_into_chunks(text_content, chunk_size=900)
    lines = [l for l in text_content.splitlines() if l.strip()]
    summary = f"{ext.upper()} document with {len(lines)} lines (~{len(text_content.split())} words)."

    return ParsedDocument(
        filename=filename,
        file_type=ext,
        file_size_bytes=len(file_bytes),
        row_count=len(lines),
        column_names=[],
        summary=summary,
        markdown_preview=text_content[:1000] if text_content else "*Empty file*",
        chunks=chunks,
    )


def parse_document(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Dispatch file bytes to appropriate parser based on extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    if ext == "csv":
        return parse_csv(file_bytes, filename)
    elif ext in ["xlsx", "xls"]:
        return parse_excel(file_bytes, filename)
    elif ext in ["docx", "doc"]:
        return parse_docx(file_bytes, filename)
    elif ext in ["md", "markdown", "txt", "json"]:
        return parse_text_or_markdown(file_bytes, filename, ext)
    else:
        # Default fallback to clean text parsing
        return parse_text_or_markdown(file_bytes, filename, ext)


def index_document_into_knowledge(
    parsed: ParsedDocument,
    tenant_id: str,
    db: Session,
    upload_dir: str = "data/uploads",
    file_bytes: bytes | None = None,
) -> InternalDocument:
    """
    Persist InternalDocument catalog entry, save raw copy to storage,
    and index semantic chunks into RawDocument with pgvector embeddings.
    """
    os.makedirs(os.path.join(upload_dir, tenant_id), exist_ok=True)
    now = datetime.now(UTC)

    # 1. Create InternalDocument catalog record
    storage_path = os.path.join(upload_dir, tenant_id, f"{int(now.timestamp())}_{parsed.filename}")
    if file_bytes:
        try:
            with open(storage_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            logger.warning(f"Could not write raw upload to disk: {e}")

    internal_doc = InternalDocument(
        tenant_id=tenant_id,
        filename=parsed.filename,
        file_type=parsed.file_type,
        file_size_bytes=parsed.file_size_bytes,
        storage_path=storage_path,
        row_count=parsed.row_count,
        column_names=parsed.column_names,
        summary=parsed.summary,
        status="indexed",
        metadata_json={
            **parsed.metadata,
            "chunk_count": len(parsed.chunks),
            "preview_snippet": parsed.markdown_preview[:500],
        },
    )
    db.add(internal_doc)
    db.flush()

    # 2. Vectorize and chunk into RawDocument knowledge base
    for idx, chunk in enumerate(parsed.chunks):
        content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        simhash_val = compute_simhash(chunk)
        if simhash_val is not None and simhash_val >= (1 << 63):
            simhash_val -= (1 << 64)
        embedding_vec = compute_deterministic_embedding(chunk, dimensions=1536)

        raw_doc = RawDocument(
            tenant_id=tenant_id,
            company_id=None,  # Internal enterprise knowledge
            source_id=None,
            url=f"internal://{parsed.filename}#chunk-{idx + 1}",

            canonical_url=f"internal://{parsed.filename}#chunk-{idx + 1}",
            content=chunk,
            content_hash=content_hash,
            simhash=simhash_val,
            provider="internal_document",
            fetched_at=now,
            metadata_json={
                "internal_doc_id": internal_doc.id,
                "filename": parsed.filename,
                "file_type": parsed.file_type,
                "chunk_index": idx,
                "total_chunks": len(parsed.chunks),
            },
            embedding=embedding_vec,
        )
        db.add(raw_doc)

        # Record in document hashes
        hash_record = DocumentHash(
            tenant_id=tenant_id,
            hash_type="sha256",
            hash_value=content_hash,
        )
        db.add(hash_record)

    db.commit()
    db.refresh(internal_doc)
    logger.info(
        f"Successfully indexed '{parsed.filename}' for tenant {tenant_id}: {len(parsed.chunks)} chunks stored in pgvector"
    )
    return internal_doc
