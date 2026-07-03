from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import shutil

app = FastAPI()

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)


class Question(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "Hello RAG"}


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