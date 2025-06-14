from fastapi import APIRouter
from pydantic import BaseModel
from app.embed_data import embed_text
from app.discourse_fetch import get_search_results
from app.utils import load_npz
import numpy as np
import os

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

EMBED_DIR = "checkpoints/embeddings"

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    query_emb = embed_text(req.question)
    scores = []
    for fname in os.listdir(EMBED_DIR):
        if fname.endswith(".npz"):
            emb = load_npz(os.path.join(EMBED_DIR, fname))
            score = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
            scores.append((score, fname))

    scores.sort(reverse=True)
    top_md = scores[0][1].replace(".npz", "")

    discourse_hits = get_search_results(req.question)
    discourse_snippet = "\n".join(post['blurb'] for post in discourse_hits.get('posts', [])[:3])

    return ChatResponse(answer=f"Top source: {top_md}\n\nDiscourse answers:\n{discourse_snippet}")