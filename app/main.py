from fastapi import FASTAPI
from pydantic import BaseModel

app = FASTAPI()

class Question(BaseModel):
    question: str

@app.get("/")
def home():
    return {"Message":"Hello RAG"}

@app.post("/ask")
def ask(question: Question):
    return {
        "received_question": question.question,
    }