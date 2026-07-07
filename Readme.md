# 📄 PDF Knowledge Assistant

A production-ready **Retrieval-Augmented Generation (RAG)** application that enables users to upload PDF documents and ask natural language questions using semantic search and Large Language Models (LLMs).

The project is being built from scratch with a focus on understanding every stage of the RAG pipeline rather than relying heavily on high-level frameworks.

---

## 🚀 Planned Features

- 📄 PDF Upload
- 📖 PDF Text Extraction
- ✂️ Multiple Chunking Strategies
  - Fixed-size Chunking
  - Semantic Chunking
  - Recursive Chunking
  - Structure-based Chunking
- 🧠 Sentence Transformer Embeddings
- 🔍 Qdrant Vector Database
- 🤖 Gemini API Integration
- 💬 Conversational Chat History
- 🗄️ PostgreSQL Integration
- 📚 Multi-document Support
- 📑 Source Citations
- 🐳 Docker Deployment
- 🌐 REST API with FastAPI

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| Backend | FastAPI, Python |
| PDF Processing | PyMuPDF |
| Embeddings | Sentence Transformers |
| Vector Database | Qdrant |
| Database | PostgreSQL |
| LLM | Gemini API |
| Deployment | Docker |

---

## 🏗️ Project Architecture

```text
PDF
 │
 ▼
Upload
 │
 ▼
Extract Text
 │
 ▼
Chunk Text
 │
 ▼
Generate Embeddings
 │
 ▼
Qdrant Vector Database
 │
 ▼
Semantic Search
 │
 ▼
Gemini API
 │
 ▼
Final Answer + Source Citations
```

---

# 📈 Development Progress

## ✅ Day 1

- Initialized project structure
- Installed FastAPI
- Created first GET endpoint
- Verified FastAPI server setup

---

## ✅ Day 2

- Learned HTTP GET & POST methods
- Implemented request validation using Pydantic
- Created `/ask` endpoint
- Tested APIs using Swagger UI

---

## ✅ Day 3

- Implemented PDF upload functionality
- Added `/upload` endpoint
- Stored uploaded PDFs locally
- Organized project folder structure

---

## ✅ Day 4

- Implemented PDF text extraction using PyMuPDF
- Created reusable `pdf_utils.py`
- Added `/extract` endpoint
- Returned extracted text preview
- Displayed character count

---

## ✅ Day 5

- Refactored request models into `schemas.py`
- Created reusable `chunking.py`
- Implemented fixed-size chunking
- Added `/chunks` endpoint
- Improved backend architecture

---

## 🚧 Upcoming Features

- Sentence Transformer Embeddings
- Qdrant Integration
- Semantic Search
- Retrieval Pipeline
- Gemini API Integration
- Chat History
- Source Citations
- Docker Deployment

---

## 🎯 Learning Goals

This project focuses on understanding and implementing the complete RAG pipeline, including:

- PDF preprocessing
- Document chunking strategies
- Embedding generation
- Vector databases
- Similarity search
- Prompt engineering
- LLM integration
- Production-ready backend architecture

---

## 📌 Status

**Work in Progress** 🚧

Currently implementing the core Retrieval-Augmented Generation (RAG) pipeline.