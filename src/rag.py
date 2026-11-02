"""Document retrieval helpers for the store policy PDF."""

from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_NAMES = ("políticas_da_loja.pdf", "politicas_da_loja.pdf")
CHROMA_DIR = DATA_DIR / "chroma_politicas"
COLLECTION_NAME = "politicas_da_loja"


def _find_pdf() -> Path:
    for filename in PDF_NAMES:
        pdf_path = DATA_DIR / filename
        if pdf_path.exists():
            return pdf_path
    expected_paths = ", ".join(str(DATA_DIR / name) for name in PDF_NAMES)
    raise FileNotFoundError(f"PDF de politicas nao encontrado. Caminhos esperados: {expected_paths}")


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n\n".join(pages).strip()
    if not text:
        raise ValueError(f"Nao foi possivel extrair texto do PDF: {pdf_path}")
    return text


def _create_chunks(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
    )
    return splitter.split_text(text)


def criar_indice_politicas() -> chromadb.Collection:
    """Extract the PDF and create or refresh its persistent Chroma collection."""
    pdf_path = _find_pdf()
    chunks = _create_chunks(_extract_text(pdf_path))
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=DefaultEmbeddingFunction(),
    )

    collection.delete(where={"source": str(pdf_path)})
    collection.add(
        ids=[f"politica-{index}" for index in range(len(chunks))],
        documents=chunks,
        metadatas=[{"source": str(pdf_path), "chunk": index} for index in range(len(chunks))],
    )
    return collection


def consultar_politicas(query: str, k: int = 3) -> str:
    """Return the most relevant policy excerpts as a single context string."""
    if not query or not query.strip():
        return "Informe uma pergunta para consultar as politicas da loja."
    if k < 1:
        return "O parametro k deve ser maior ou igual a 1."

    try:
        collection = criar_indice_politicas()
        result = collection.query(
            query_texts=[query.strip()],
            n_results=min(k, collection.count()),
        )
    except (OSError, ValueError, RuntimeError) as error:
        return f"Nao foi possivel consultar as politicas da loja: {error}"
    except Exception as error:
        return f"Nao foi possivel consultar as politicas da loja: {error}"

    documents = result.get("documents", [[]])[0]
    if not documents:
        return "Nenhum trecho relevante das politicas foi encontrado."
    return "\n\n---\n\n".join(documents)