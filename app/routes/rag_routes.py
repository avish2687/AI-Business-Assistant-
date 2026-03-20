from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Optional
from app.services.rag_service import (
    ingest_documents,
    query_documents,
    similarity_search,
    delete_vectorstore,
)

router = APIRouter()


# --- Request / Response Models ---

class IngestRequest(BaseModel):
    texts: List[str] = Field(..., description="List of text documents to ingest")
    sources: Optional[List[str]] = Field(None, description="Source labels for each document")
    store_name: str = Field("default", description="Name of the vectorstore")

class QueryRequest(BaseModel):
    question: str = Field(..., example="What is the company's return policy?")
    store_name: str = Field("default")
    k: int = Field(4, ge=1, le=10, description="Number of chunks to retrieve")

class SearchRequest(BaseModel):
    query: str = Field(..., example="product pricing information")
    store_name: str = Field("default")
    k: int = Field(5, ge=1, le=10)


# --- Endpoints ---

@router.post("/ingest")
def ingest(req: IngestRequest):
    """Ingest text documents into the FAISS vectorstore."""
    try:
        metadatas = None
        if req.sources:
            if len(req.sources) != len(req.texts):
                raise HTTPException(
                    status_code=400,
                    detail="sources list must match texts list in length"
                )
            metadatas = [{"source": s} for s in req.sources]

        result = ingest_documents(req.texts, metadatas, req.store_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-file")
async def ingest_file(
    file: UploadFile = File(...),
    store_name: str = Form("default")
):
    """Upload and ingest a .txt file into the vectorstore."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")
    try:
        content = await file.read()
        text = content.decode("utf-8")
        result = ingest_documents(
            [text],
            [{"source": file.filename}],
            store_name
        )
        return {"filename": file.filename, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
def query(req: QueryRequest):
    """Ask a question and get an answer from ingested documents (RAG)."""
    try:
        result = query_documents(req.question, req.store_name, req.k)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
def search(req: SearchRequest):
    """Return the most similar document chunks for a query (no LLM)."""
    try:
        results = similarity_search(req.query, req.store_name, req.k)
        return {"query": req.query, "results": results}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/store/{store_name}")
def delete_store(store_name: str):
    """Delete a vectorstore by name."""
    try:
        result = delete_vectorstore(store_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
