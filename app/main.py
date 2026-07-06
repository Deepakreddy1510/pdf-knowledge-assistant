from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil

from app.schemas import Question, PDFRequest
from app.pdf_utils import extract_text
from app.chunking import chunk_pdf_pages
from app.embedding import embed_chunks

app = FastAPI()

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)


@app.get("/")
def home():
    return {
        "message": "Hello RAG"
    }


@app.post("/ask")
def ask(question: Question):
    return {
        "received_question": question.question
    }


@app.post("/upload")
def upload_pdf(file: UploadFile = File(...)):

    file_path = UPLOAD_FOLDER / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": file.filename,
        "status": "uploaded successfully"
    }


@app.post("/extract")
def extract_pdf(request: PDFRequest):

    file_path = UPLOAD_FOLDER / request.filename

    if not file_path.exists():
        return {
            "error": "File not found"
        }

    text = extract_text(file_path)

    return {
        "filename": request.filename,
        "characters": len(text),
        "preview": text[:500]
    }


@app.post("/chunks")
def create_chunks(request: PDFRequest):

    file_path = UPLOAD_FOLDER / request.filename

    if not file_path.exists():
        return {
            "error": "File not found"
        }

    text = extract_text(file_path)

    pages_and_texts = [
        {
            "page_number": 1,
            "page_text": text
        }
    ]

    chunks = chunk_pdf_pages(
        pages_and_texts,
        chunk_size=500
    )

    return {
        "filename": request.filename,
        "total_chunks": len(chunks),
        "first_chunk": chunks[0]["chunk_text"] if chunks else ""
    }

@app.post("/embed")
def embed_pdf(request: PDFRequest):

    file_path = UPLOAD_FOLDER / request.filename

    if not file_path.exists():
        return {
            "error": "File not found"
        }

    text = extract_text(file_path)

    pages_and_texts = [
        {
            "page_number": 1,
            "page_text": text,
        }
    ]

    chunks = chunk_pdf_pages(
        pages_and_texts,
        chunk_size=500,
    )

    chunk_texts = [
        chunk["chunk_text"]
        for chunk in chunks
    ]

    embeddings = embed_chunks(chunk_texts)

    return {
        "filename": request.filename,
        "total_chunks": len(chunk_texts),
        "embedding_dimension": len(embeddings[0]),
        "first_embedding": embeddings[0][:10],   # first 10 values only
    }