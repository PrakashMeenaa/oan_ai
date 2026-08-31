import numpy as np
from fastembed import TextEmbedding
from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedding_model() -> TextEmbedding:
    return TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")


def create_embedding(text: str) -> list[float]:
    model = get_embedding_model()
    raw_embedding = next(model.embed([text]))
    normalized = raw_embedding / np.linalg.norm(raw_embedding)
    return normalized.tolist()