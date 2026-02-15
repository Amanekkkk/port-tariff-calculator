from pathlib import Path
from app.config import CHROMA_PERSIST_DIR, get_tariff_pdf_path_or_raise
from app.pdf_loader import chunk_text, load_pdf_text


def build_vector_store(force_rebuild: bool = False) -> "ChromaDB":
    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions
    except ImportError:
        raise ImportError(
            "chromadb and sentence-transformers required. Run: pip install chromadb sentence-transformers"
        )

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    client = chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    collection_name = "port_tariffs"

    if force_rebuild or not _collection_exists(client, collection_name):
        _build_collection(client, collection_name, embedding_fn)
    else:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embedding_fn,
        )
        if collection.count() == 0:
            _build_collection(client, collection_name, embedding_fn)

    return client.get_collection(
        name=collection_name,
        embedding_function=embedding_fn,
    )


def _collection_exists(client, name: str) -> bool:
    try:
        client.get_collection(name=name)
        return True
    except Exception:
        return False


def _build_collection(client, collection_name: str, embedding_fn) -> None:
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass

    pdf_path = get_tariff_pdf_path_or_raise()
    text = load_pdf_text(pdf_path)
    chunks = chunk_text(text)

    documents = [c[0] for c in chunks]
    metadatas = [{"chunk_id": i, "start": c[1]} for i, c in enumerate(chunks)]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"description": "South African port tariff document chunks"},
    )

    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_meta = metadatas[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        collection.add(
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids,
        )


def retrieve_tariff_context(collection, query: str, top_k: int = 12) -> str:
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents"],
    )
    docs = results["documents"][0] if results["documents"] else []
    return "\n\n---\n\n".join(docs)


def retrieve_tariff_context_multi(
    collection,
    vessel,
    port: str,
    top_k_per_query: int = 5,
) -> str:
    vessel_desc = f"GT {vessel.gt}, NT {vessel.nt}, LOA {vessel.loa}m, beam {vessel.beam}m"
    queries = [
        f"light dues calculation formula rate {port} {vessel_desc}",
        f"port dues berth dues calculation {port} gross tonnage net tonnage days alongside {vessel_desc}",
        f"towage dues tug charges {port} LOA beam draft {vessel_desc}",
        f"VTS vehicle traffic services dues {port} {vessel_desc}",
        f"pilotage dues pilot charges {port} LOA GT {vessel_desc}",
        f"running of vessel lines mooring line handling dues {port} {vessel_desc}",
    ]
    seen = set()
    all_docs = []
    for q in queries:
        results = collection.query(
            query_texts=[q],
            n_results=min(top_k_per_query, collection.count()),
            include=["documents"],
        )
        docs = results["documents"][0] if results["documents"] else []
        for d in docs:
            h = hash(d[:200])
            if h not in seen:
                seen.add(h)
                all_docs.append(d)
    return "\n\n---\n\n".join(all_docs) if all_docs else ""
