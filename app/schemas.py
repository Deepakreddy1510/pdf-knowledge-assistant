from pydantic import BaseModel


class Question(BaseModel):
    question: str


class PDFRequest(BaseModel):
    filename: str