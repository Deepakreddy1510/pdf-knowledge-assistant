from fastapi import FASTAPI

app = FASTAPI()

@app.get("/")
def home():
    return {"Message":"Hello RAG"}