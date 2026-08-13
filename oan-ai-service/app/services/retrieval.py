import re
from concurrent.futures import ThreadPoolExecutor
from app.core.supabase import get_supabase
from app.services.embeddings import create_embedding

PRODUCT_KEYWORDS = [
    "product", "defoamer", "anticaking", "antidusting", "granulation",
    "plasticizer", "stearate", "flotation", "flocculant", "collector",
    "filtration", "scale", "inhibitor", "specification", "grade", "density",
    "ph", "solubility", "appearance", "formulation", "chemical", "additive",
    "fertilizer", "phosphoric", "mining", "dop", "dbp", "dotp", "dinp",
    "esbo", "dom", "calcium", "zinc", "magnesium", "aluminium",
    "urea", "npk", "dap", "map", "ssp", "granule", "foam", "dust",
    "pvc", "cable", "wire", "coating", "adhesive", "leather", "packaging",
    "recommend", "suggest", "best", "suitable", "use", "application",
    "what do you have", "what products", "which product",
]


def extract_product_codes(query: str) -> list[str]:
    matches = re.findall(r'\bOAN\s+[A-Z]{1,6}(?:\s+\d{1,5})?\b', query, re.IGNORECASE)
    cleaned = [m.strip() for m in matches]
    return cleaned

APPLICATION_SEARCH_MAP = {
    "urea": "OAN UA",
    "granular fertilizer": "OAN AN",
    "water soluble": "OAN 505",
    "phosphoric acid": "OAN D 1009",
    "silica flotation": "OAN AMFLOAT",
    "carbonate flotation": "OAN FLOAT",
}


def get_application_search_terms(query: str) -> list[str]:
    query_lower = query.lower()
    terms = []
    for keyword, product_prefix in APPLICATION_SEARCH_MAP.items():
        if keyword in query_lower:
            terms.append(product_prefix)
    return terms


def is_product_question(query: str) -> bool:
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in PRODUCT_KEYWORDS)


def text_search_chunks(term: str, result_count: int = 6) -> list[dict]:
    supabase = get_supabase()
    result = supabase.rpc(
        "search_oan_content",
        {"search_term": term, "result_count": result_count},
    ).execute()
    return result.data or []


def vector_search_chunks(
    query_embedding: list[float],
    threshold: float,
    match_count: int,
    product_only: bool = False,
) -> list[dict]:
    supabase = get_supabase()
    result = supabase.rpc(
        "match_oan_documents",
        {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": match_count,
        },
    ).execute()

    chunks = result.data or []

    if product_only:
        chunks = [
            c for c in chunks
            if c.get("metadata", {}).get("document_type") == "product_catalog"
        ]

    return chunks


def retrieve_relevant_chunks(query: str, match_count: int = 8) -> list[dict]:
    product_codes = extract_product_codes(query)
    application_terms = get_application_search_terms(query)
    search_terms = product_codes + application_terms

    if search_terms:
        with ThreadPoolExecutor(max_workers=len(search_terms)) as executor:
            batches = executor.map(lambda term: text_search_chunks(term, result_count=6), search_terms)
        text_results = [chunk for batch in batches for chunk in batch]

        if text_results:
            seen_ids: set[str] = set()
            unique = []
            for chunk in text_results:
                chunk_id = str(chunk.get("id", ""))
                if chunk_id not in seen_ids:
                    seen_ids.add(chunk_id)
                    unique.append(chunk)
            return unique[:match_count]

    query_embedding = create_embedding(query)

    if is_product_question(query):
        product_chunks = vector_search_chunks(
            query_embedding, threshold=0.2, match_count=15, product_only=True
        )
        if len(product_chunks) >= 2:
            return product_chunks[:match_count]

    return vector_search_chunks(
        query_embedding, threshold=0.2, match_count=match_count
    )