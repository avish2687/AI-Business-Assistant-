import os
from typing import List
from pathlib import Path

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

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
    return FAISS.from_documents(documents, embeddings)


def save_vectorstore(vectorstore: FAISS, name: str = "default"):
    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(VECTOR_STORE_PATH / name))


def load_vectorstore(name: str = "default") -> FAISS:
    path = VECTOR_STORE_PATH / name
    if not path.exists():
        raise FileNotFoundError(f"Vectorstore '{name}' not found. Please ingest documents first.")
    embeddings = get_embeddings()
    return FAISS.load_local(str(path), embeddings, allow_dangerous_deserialization=True)


def ingest_documents(texts: List[str], metadatas: List[dict] = None, store_name: str = "default"):
    vectorstore = build_vectorstore_from_texts(texts, metadatas)
    try:
        existing = load_vectorstore(store_name)
        existing.merge_from(vectorstore)
        save_vectorstore(existing, store_name)
    except FileNotFoundError:
        save_vectorstore(vectorstore, store_name)
    return {"status": "success", "chunks_stored": len(texts)}


def query_documents(question: str, store_name: str = "default", k: int = 4) -> dict:
    vectorstore = load_vectorstore(store_name)

    qa_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""You are a knowledgeable business assistant. Use the following context to answer the question.

Context:
{context}

Question: {question}

Answer based strictly on the provided context. If insufficient info, say so.
Answer:"""
    )

    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})

    # New LangChain LCEL chain (no deprecated RetrievalQA)
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | qa_prompt
        | get_llm()
        | StrOutputParser()
    )

    answer = chain.invoke(question)

    # Get source docs separately for metadata
    source_docs = retriever.invoke(question)
    sources = list({doc.metadata.get("source", "unknown") for doc in source_docs})

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": len(source_docs)
    }


def similarity_search(query: str, store_name: str = "default", k: int = 5) -> List[dict]:
    vectorstore = load_vectorstore(store_name)
    docs = vectorstore.similarity_search_with_score(query, k=k)
    return [
        {"content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
        for doc, score in docs
    ]


def delete_vectorstore(name: str = "default"):
    import shutil
    path = VECTOR_STORE_PATH / name
    if path.exists():
        shutil.rmtree(path)
        return {"status": "deleted", "store": name}
    return {"status": "not_found", "store": name}