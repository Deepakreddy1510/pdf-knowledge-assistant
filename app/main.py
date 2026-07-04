from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
from app.pdf_utils import extract_text
import shutil

app = FastAPI()

# Create uploads folder if it doesn't exist
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)


# -------------------------
# Pydantic Models
# -------------------------

class Question(BaseModel):
    question: str


class PDFRequest(BaseModel):
    filename: str


# -------------------------
# Routes
# -------------------------

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