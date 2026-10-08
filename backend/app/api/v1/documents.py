"""Internal enterprise documents upload, listing, and knowledge management router."""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_and_tenant
from app.core.logging import get_logger
from app.db.models import InternalDocument, RawDocument
from app.db.session import get_db
from app.ingestion.doc_parser import index_document_into_knowledge, parse_document

logger = get_logger("api.documents")
router = APIRouter(prefix="/documents", tags=["Documents"])

SUPPORTED_EXTENSIONS = {
    "csv",
    "xlsx",
    "xls",
    "docx",
    "doc",
    "md",
    "markdown",
    "txt",
    "json",
}


@router.get("")
def list_documents(
    file_type: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """List uploaded enterprise documentation for current tenant."""
    _, tenant_id = user_and_tenant
    q = db.query(InternalDocument).filter(InternalDocument.tenant_id == tenant_id)
    if file_type:
        q = q.filter(InternalDocument.file_type == file_type.lower())

    docs = q.order_by(InternalDocument.created_at.desc()).limit(limit).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size_bytes": d.file_size_bytes,
            "row_count": d.row_count,
            "column_names": d.column_names or [],
            "summary": d.summary,
            "status": d.status,
            "chunk_count": d.metadata_json.get("chunk_count", 0) if d.metadata_json else 0,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """
    Upload and index enterprise document (CSV, XLSX, DOCX, MD, TXT, JSON).
    Parses schemas, generates preview, extracts statistics, and embeds
    semantic chunks into pgvector hybrid memory.
    """
    user, tenant_id = user_and_tenant

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a valid filename",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Read file bytes (cap at 25MB for safety)
    file_bytes = await file.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds 25MB limit",
        )

    try:
        parsed = parse_document(file_bytes=file_bytes, filename=file.filename)
        internal_doc = index_document_into_knowledge(
            parsed=parsed,
            tenant_id=tenant_id,
            db=db,
            file_bytes=file_bytes,
        )

        return {
            "id": internal_doc.id,
            "filename": internal_doc.filename,
            "file_type": internal_doc.file_type,
            "file_size_bytes": internal_doc.file_size_bytes,
            "row_count": internal_doc.row_count,
            "column_names": internal_doc.column_names,
            "summary": internal_doc.summary,
            "status": internal_doc.status,
            "chunks_indexed": len(parsed.chunks),
            "created_at": internal_doc.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error parsing document '{file.filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process document: {str(e)}",
        ) from e


@router.get("/{doc_id}")
def get_document(
    doc_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Retrieve document metadata and preview snippet."""
    _, tenant_id = user_and_tenant
    doc = (
        db.query(InternalDocument)
        .filter(
            InternalDocument.id == doc_id,
            InternalDocument.tenant_id == tenant_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    chunks = (
        db.query(RawDocument)
        .filter(
            RawDocument.tenant_id == tenant_id,
            RawDocument.source_id == f"internal-doc-{doc.id}",
        )
        .all()
    )

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size_bytes": doc.file_size_bytes,
        "row_count": doc.row_count,
        "column_names": doc.column_names,
        "summary": doc.summary,
        "status": doc.status,
        "preview_snippet": doc.metadata_json.get("preview_snippet", "") if doc.metadata_json else "",
        "total_chunks": len(chunks),
        "created_at": doc.created_at.isoformat(),
    }


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    user_and_tenant=Depends(get_current_user_and_tenant),
    db: Session = Depends(get_db),
):
    """Delete document catalog entry and its indexed knowledge chunks."""
    _, tenant_id = user_and_tenant
    doc = (
        db.query(InternalDocument)
        .filter(
            InternalDocument.id == doc_id,
            InternalDocument.tenant_id == tenant_id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete indexed chunks from raw_documents
    db.query(RawDocument).filter(
        RawDocument.tenant_id == tenant_id,
        RawDocument.source_id == f"internal-doc-{doc.id}",
    ).delete(synchronize_session=False)

    # Clean up file on disk if exists
    if doc.storage_path and os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
        except Exception as e:
            logger.warning(f"Could not remove local file {doc.storage_path}: {e}")

    db.delete(doc)
    db.commit()
