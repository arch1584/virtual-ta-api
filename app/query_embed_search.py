import numpy as np
import requests
import os
from utils import chunk_text

AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
AIPIPE_BASE = "https://aipipe.org"

def semantic_search(query, embedding_file, model_name="text-embedding-3-small", top_k=5):
    # Load embeddings metadata and corresponding texts
    data = np.load(embedding_file, allow_pickle=True)
    metadata = data["metadata"]
    docs = [m["content"] for m in metadata]  # all text/image chunks

    # Chunk the query if needed
    query_chunks = chunk_text(query)
    
    # Prepare API request
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "docs": docs,           # corpus
        "topics": query_chunks, # query (can be chunked)
        "model": model_name,
        "precision": 5
    }
    response = requests.post(
        f"{AIPIPE_BASE}/similarity",
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    sim_matrix = response.json()["similarity"]  # shape: [len(docs), len(query_chunks)]

    # For each doc, take max similarity over all query chunks
    scores = np.max(np.array(sim_matrix), axis=1)
    top_indices = scores.argsort()[-top_k:][::-1]
    return [metadata[i] for i in top_indices]

if __name__ == "__main__":
    query = input("Enter your query: ")
    results = semantic_search(query, "data/embeddings/combined_embeddings.npz")
    for res in results:
        print(res)
