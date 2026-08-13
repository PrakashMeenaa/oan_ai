import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.supabase import get_supabase
from app.services.embeddings import create_embedding

DOCUMENTS_DIR = Path("documents")
CHUNK_SIZE = 600
CHUNK_OVERLAP = 80

PRODUCT_CATALOG_FILES = {
    "OAN_Group_Products_Services_RAG.pdf",
}


def classify_document(filename: str) -> str:
    name = filename.lower()
    if filename in PRODUCT_CATALOG_FILES:
        return "product_catalog"
    if any(k in name for k in ["annual report", "fy 20", "annual return"]):
        return "annual_report"
    if any(k in name for k in ["policy", "code", "conduct", "whistle", "csr", "familiari"]):
        return "policy"
    if any(k in name for k in ["consent", "agreement", "mou", "contract", "drhp", "rta", "sebi"]):
        return "legal"
    return "corporate"


def load_all_documents() -> list:
    all_docs = []
    for pdf_path in DOCUMENTS_DIR.glob("**/*.pdf"):
        print(f"  Loading: {pdf_path.name}")
        try:
            docs = PyPDFLoader(str(pdf_path)).load()
            doc_type = classify_document(pdf_path.name)
            for doc in docs:
                doc.metadata["document_type"] = doc_type
                doc.metadata["filename"] = pdf_path.name
            all_docs.extend(docs)
        except Exception as e:
            print(f"  WARNING: Could not load {pdf_path.name}: {e}")

    for txt_path in DOCUMENTS_DIR.glob("**/*.txt"):
        print(f"  Loading: {txt_path.name}")
        try:
            docs = TextLoader(str(txt_path), encoding="utf-8").load()
            for doc in docs:
                doc.metadata["document_type"] = "product_catalog"
                doc.metadata["filename"] = txt_path.name
            all_docs.extend(docs)
        except Exception as e:
            print(f"  WARNING: Could not load {txt_path.name}: {e}")

    return all_docs


def split_into_chunks(documents: list) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_documents(documents)


def store_chunks(chunks: list) -> None:
    supabase = get_supabase()
    total = len(chunks)
    counts: dict[str, int] = {}

    for index, chunk in enumerate(chunks):
        filename = chunk.metadata.get("filename", "unknown")
        doc_type = chunk.metadata.get("document_type", "corporate")
        counts[doc_type] = counts.get(doc_type, 0) + 1

        if (index + 1) % 20 == 0 or index == 0:
            print(f"  [{index + 1}/{total}] {doc_type}: {filename}")

        embedding = create_embedding(chunk.page_content)

        supabase.table("oan_document_chunks").insert({
            "source_file": filename,
            "chunk_index": index,
            "content": chunk.page_content,
            "embedding": embedding,
            "metadata": {
                "source": filename,
                "page": chunk.metadata.get("page", 0),
                "document_type": doc_type,
            },
        }).execute()

    print(f"\n✓ Done — {total} chunks stored")
    for doc_type, count in counts.items():
        print(f"  {doc_type}: {count} chunks")


def main() -> None:
    if not DOCUMENTS_DIR.exists():
        print("Error: 'documents/' folder not found.")
        return

    print("Loading documents...")
    documents = load_all_documents()

    if not documents:
        print("No documents found.")
        return

    print(f"\nLoaded {len(documents)} pages. Splitting into chunks...")
    chunks = split_into_chunks(documents)
    print(f"Created {len(chunks)} chunks. Storing in Supabase...\n")
    store_chunks(chunks)


if __name__ == "__main__":
    main()