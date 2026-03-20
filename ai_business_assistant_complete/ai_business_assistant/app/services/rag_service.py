import os
import pickle
from typing import List
from pathlib import Path

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain.prompts import PromptTemplate

from app.core.config import settings

VECTOR_STORE_PATH = Path("data/vectorstore")


def get_embeddings():
    return OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)


def get_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        openai_api_key=settings.OPENAI_API_KEY,
    )


def build_vectorstore_from_texts(texts: List[str], metadatas: List[dict] = None) -> FAISS:
    """Build a FAISS vectorstore from a list of text chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    documents = []
    for i, text in enumerate(texts):
        chunks = splitter.split_text(text)
        meta = metadatas[i] if metadatas else {"source": f"doc_{i}"}
        for chunk in chunks:
            documents.append(Document(page_content=chunk, metadata=meta))

    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore


def save_vectorstore(vectorstore: FAISS, name: str = "default"):
    """Persist FAISS vectorstore to disk."""
    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTOR_STORE_PATH / name))


def load_vectorstore(name: str = "default") -> FAISS:
    """Load FAISS vectorstore from disk."""
    path = VECTOR_STORE_PATH / name
    if not path.exists():
        raise FileNotFoundError(f"Vectorstore '{name}' not found. Please ingest documents first.")
    embeddings = get_embeddings()
    return FAISS.load_local(str(path), embeddings, allow_dangerous_deserialization=True)


def ingest_documents(texts: List[str], metadatas: List[dict] = None, store_name: str = "default"):
    """Ingest documents into the vectorstore (creates or updates)."""
    vectorstore = build_vectorstore_from_texts(texts, metadatas)

    # Merge with existing store if it exists
    try:
        existing = load_vectorstore(store_name)
        existing.merge_from(vectorstore)
        save_vectorstore(existing, store_name)
    except FileNotFoundError:
        save_vectorstore(vectorstore, store_name)

    return {"status": "success", "chunks_stored": len(texts)}


def query_documents(question: str, store_name: str = "default", k: int = 4) -> dict:
    """Answer a question using RAG over stored documents."""
    vectorstore = load_vectorstore(store_name)

    qa_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""You are a knowledgeable business assistant. Use the following context to answer the question accurately and concisely.

Context:
{context}

Question: {question}

Answer based strictly on the provided context. If the context doesn't contain enough information, say so clearly.
Answer:"""
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=get_llm(),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": qa_prompt}
    )

    result = qa_chain.invoke({"query": question})

    sources = list({
        doc.metadata.get("source", "unknown")
        for doc in result.get("source_documents", [])
    })

    return {
        "answer": result["result"],
        "sources": sources,
        "retrieved_chunks": len(result.get("source_documents", []))
    }


def similarity_search(query: str, store_name: str = "default", k: int = 5) -> List[dict]:
    """Return top-k similar document chunks for a query."""
    vectorstore = load_vectorstore(store_name)
    docs = vectorstore.similarity_search_with_score(query, k=k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)
        }
        for doc, score in docs
    ]


def delete_vectorstore(name: str = "default"):
    """Delete a vectorstore from disk."""
    import shutil
    path = VECTOR_STORE_PATH / name
    if path.exists():
        shutil.rmtree(path)
        return {"status": "deleted", "store": name}
    return {"status": "not_found", "store": name}
