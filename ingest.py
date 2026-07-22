# ingest.py
#
# Install dependencies:
# python -m pip install pymupdf sentence-transformers supabase tqdm python-dotenv torch

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import fitz  # PyMuPDF
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import Client, create_client
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------

ENV_PATH = Path(__file__).resolve().parent / ".env"

if not ENV_PATH.exists():
    raise FileNotFoundError(
        f"Could not find .env at: {ENV_PATH}\n"
        "Create .env in the same folder as ingest.py."
    )

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

print(f"Loaded environment file: {ENV_PATH}")


def get_required_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""

    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Missing environment variable: {name}. "
            f"Add it to {ENV_PATH}."
        )

    return value.strip()


# IMPORTANT: get_required_env() must be defined before these lines.
SUPABASE_URL = get_required_env("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = get_required_env(
    "SUPABASE_SERVICE_ROLE_KEY"
)

parsed_url = urlparse(SUPABASE_URL)

if (
    parsed_url.scheme not in {"http", "https"}
    or not parsed_url.netloc
):
    raise RuntimeError(
        "SUPABASE_URL is invalid.\n"
        "Expected format:\n"
        "https://your-project-id.supabase.co"
    )

if parsed_url.path not in {"", "/"}:
    raise RuntimeError(
        "SUPABASE_URL must be the base project URL only.\n\n"
        "Incorrect:\n"
        "https://your-project-id.supabase.co/rest/v1/\n\n"
        "Correct:\n"
        "https://your-project-id.supabase.co"
    )

print(f"Supabase URL: {SUPABASE_URL}")
print("Supabase service-role key loaded successfully.")

# GEMINI_API_KEY is not required in ingest.py.
# Gemini is used later in rag_chat.py for final answer generation.


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PDF_PATH = "Human-Nutrition-2020-Edition-1598491699.pdf"
DOC_ID = "nutrition-v1"

# Local open-source embeddings. No OpenAI key is required.
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIMENSION = 384

BATCH_EMBED = 64
BATCH_INSERT = 100

SENTS_PER_CHUNK = 5
SENT_OVERLAP = 1
MAX_TOKENS = 220
MIN_TOKENS = 30


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalize whitespace and repair words split across PDF line breaks."""

    text = text.replace("\r", " ")

    # Example: "nutri-\n tion" -> "nutrition"
    text = re.sub(r"-\s*\n\s*", "", text)

    # Replace remaining line breaks and repeated spaces.
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences using punctuation boundaries."""

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def count_tokens(
    text: str,
    tokenizer,
) -> int:
    """Count tokens without printing overlength warnings."""

    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        verbose=False,
    )

    return len(encoded["input_ids"])


def chunk_page_by_sentences(
    text: str,
    tokenizer: Any,
    sents_per_chunk: int = SENTS_PER_CHUNK,
    overlap: int = SENT_OVERLAP,
    max_tokens: int = MAX_TOKENS,
    min_tokens: int = MIN_TOKENS,
) -> Iterator[str]:
    """Split one PDF page into overlapping sentence chunks."""

    sentences = split_sentences(text)

    index = 0
    step = max(1, sents_per_chunk - overlap)

    while index < len(sentences):
        piece = sentences[
            index:index + sents_per_chunk
        ]

        if not piece:
            break

        chunk = " ".join(piece)
        chunk_token_count = count_tokens(
            chunk,
            tokenizer,
        )

        # Trim complete sentences from the end until the chunk fits.
        while (
            max_tokens
            and chunk_token_count > max_tokens
            and len(piece) > 1
        ):
            piece = piece[:-1]
            chunk = " ".join(piece)
            chunk_token_count = count_tokens(
                chunk,
                tokenizer,
            )

        if chunk_token_count >= min_tokens:
            yield chunk

        index += step


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def pdf_pages(
    path: str,
) -> Iterator[tuple[int, str]]:
    """Yield one-based page numbers and cleaned text."""

    pdf_path = Path(path)

    if not pdf_path.is_absolute():
        pdf_path = Path(__file__).resolve().parent / pdf_path

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF file was not found: {pdf_path.resolve()}"
        )

    document = fitz.open(pdf_path)

    try:
        for page_index in range(len(document)):
            raw_text = (
                document[page_index].get_text("text")
                or ""
            )

            yield (
                page_index + 1,
                clean_text(raw_text),
            )
    finally:
        document.close()


# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------

def load_embedding_model() -> SentenceTransformer:
    """Load BGE-M3 on GPU when available, otherwise on CPU."""

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Embedding device: {device}")

    model = SentenceTransformer(
        EMBED_MODEL,
        device=device,
    )

    model.max_seq_length = 256

    # Support both newer and older sentence-transformers versions.
    if hasattr(model, "get_embedding_dimension"):
        actual_dimension = model.get_embedding_dimension()
    else:
        actual_dimension = model.get_sentence_embedding_dimension()

    if actual_dimension != EMBED_DIMENSION:
        raise RuntimeError(
            "Embedding dimension mismatch. "
            f"Expected {EMBED_DIMENSION}, "
            f"but the model returned {actual_dimension}."
        )

    return model


# ---------------------------------------------------------------------------
# Build chunks and embeddings
# ---------------------------------------------------------------------------

def build_chunks(
    pages: list[tuple[int, str]],
    embedding_model: SentenceTransformer,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Create document chunks and matching metadata."""

    inputs: list[str] = []
    metadata: list[dict[str, Any]] = []

    print(
        f"Chunking document using {SENTS_PER_CHUNK} sentences "
        f"per chunk with {SENT_OVERLAP} sentence overlap..."
    )

    for page_number, page_text in pages:
        if not page_text:
            continue

        for chunk in chunk_page_by_sentences(
            text=page_text,
            tokenizer=embedding_model.tokenizer,
        ):
            inputs.append(chunk)

            metadata.append(
                {
                    "page": page_number,
                    "source": PDF_PATH,
                    "embedding_model": EMBED_MODEL,
                }
            )

    return inputs, metadata


def generate_embeddings(
    model: SentenceTransformer,
    inputs: list[str],
) -> list[list[float]]:
    """Generate normalized BGE-M3 embeddings locally."""

    vectors: list[list[float]] = []

    print("Generating local embeddings...")

    for start_index in tqdm(
        range(0, len(inputs), BATCH_EMBED),
        desc="Embedding",
    ):
        batch = inputs[
            start_index:start_index + BATCH_EMBED
        ]

        batch_vectors = model.encode(
            batch,
            batch_size=BATCH_EMBED,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        vectors.extend(batch_vectors.tolist())

    return vectors


# ---------------------------------------------------------------------------
# Supabase operations
# ---------------------------------------------------------------------------

def verify_supabase_connection(
    supabase: Client,
) -> None:
    """Verify access to the chunks table before loading the large model."""

    print("Checking Supabase connection...")

    try:
        response = (
            supabase.table("chunks")
            .select("id")
            .limit(1)
            .execute()
        )
    except Exception as error:
        raise RuntimeError(
            "Could not access the Supabase 'chunks' table.\n"
            "Check that:\n"
            "1. SUPABASE_URL is the base URL ending in .supabase.co\n"
            "2. SUPABASE_SERVICE_ROLE_KEY is valid\n"
            "3. public.chunks exists\n"
            "4. chunks.embedding is vector(1024)"
        ) from error

    print("Supabase connection successful.")
    print(f"Connection test returned {len(response.data or [])} row(s).")


def delete_existing_document_chunks(
    supabase: Client,
) -> None:
    """Delete existing rows for this document."""

    print(
        f"Removing existing chunks for doc_id={DOC_ID}..."
    )

    supabase.table("chunks").delete().eq(
        "doc_id",
        DOC_ID,
    ).execute()


def upload_rows(
    supabase: Client,
    rows: list[dict[str, Any]],
) -> None:
    """Upload rows to Supabase in batches."""

    print("Uploading chunks to Supabase...")

    for start_index in tqdm(
        range(0, len(rows), BATCH_INSERT),
        desc="Uploading",
    ):
        batch = rows[
            start_index:start_index + BATCH_INSERT
        ]

        supabase.table("chunks").insert(
            batch
        ).execute()


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def main() -> None:
    """Extract, chunk, embed, and upload the configured PDF."""

    supabase: Client = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
    )

    # Fail early if the URL, key, or table is incorrect.
    verify_supabase_connection(supabase)

    embedding_model = load_embedding_model()

    print("Reading PDF by pages...")
    pages = list(pdf_pages(PDF_PATH))

    print(f"Extracted {len(pages)} PDF pages.")

    inputs, metadata = build_chunks(
        pages=pages,
        embedding_model=embedding_model,
    )

    if not inputs:
        raise RuntimeError(
            "No chunks were created. "
            "Check the PDF content and chunk settings."
        )

    print(
        f"Built {len(inputs)} chunks from {PDF_PATH}."
    )

    vectors = generate_embeddings(
        model=embedding_model,
        inputs=inputs,
    )

    if not (
        len(inputs)
        == len(metadata)
        == len(vectors)
    ):
        raise RuntimeError(
            "The number of chunks, metadata records, "
            "and embeddings does not match."
        )

    rows: list[dict[str, Any]] = []

    for chunk_index, (
        content,
        embedding,
        chunk_metadata,
    ) in enumerate(
        zip(inputs, vectors, metadata)
    ):
        rows.append(
            {
                "doc_id": DOC_ID,
                "chunk_index": chunk_index,
                "content": content,
                "metadata": chunk_metadata,
                "embedding": embedding,
            }
        )

    # Delete old rows only after the replacement data is ready.
    delete_existing_document_chunks(supabase)

    upload_rows(
        supabase=supabase,
        rows=rows,
    )

    print(
        f"Done! Inserted {len(rows)} chunks "
        f"for doc_id={DOC_ID}."
    )


if __name__ == "__main__":
    main()