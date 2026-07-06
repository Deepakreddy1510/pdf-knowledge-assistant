from sentence_transformers import SentenceTransformer

# Load the embedding model once when the application starts
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of text chunks.

    Args:
        chunks: List of text chunks.

    Returns:
        List of embedding vectors.
    """

    embeddings = embedding_model.encode(
        chunks,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()