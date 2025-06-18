from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import base64
import asyncio
import os
import tempfile
import numpy as np

from app.discourse_fetch import fetch_relevant_posts
from app.json_to_md import json_to_md
from app.embed_data import embed_md_files, embed_text
from app.utils import get_image_description, get_url_text
from app.retriever import generate_answer

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    image: Optional[str] = None
    url: Optional[str] = None

class Link(BaseModel):
    url: str
    text: str

class ChatResponse(BaseModel):
    answer: str
    links: List[Link]

# Paths to permanent data
COURSE_MD_DIR = "data/course_content_md"

@app.post("/api/", response_model=ChatResponse)
async def get_response(req: ChatRequest):
    try:
        async with asyncio.timeout(30):
            question = f"Question: {req.question}"

           
            if req.image:
                try:
                    alt_text = get_image_description(req.image)
                    question += f"\nImage description: {alt_text}"
                except Exception as e:
                    raise HTTPException(400, f"Image processing failed: {str(e)}")
                
            url_text = ""
            if req.url:
                try:
                    url_text = get_url_text(req.url)
                    question += f"\nURL content: {url_text}"
                except Exception as e:
                    raise HTTPException(400, f"URL fetching failed: {str(e)}")


            with tempfile.TemporaryDirectory() as tmpdir:
                discourse_json_path = os.path.join(tmpdir, "latest.json")
                fetch_relevant_posts(question, out_file=discourse_json_path)
                if not os.path.exists(discourse_json_path) or os.path.getsize(discourse_json_path) == 0:
                    raise HTTPException(404, "No relevant Discourse posts found.")

                discourse_md_dir = os.path.join(tmpdir, "md")
                json_to_md(discourse_json_path, discourse_md_dir)
                if not os.path.exists(discourse_md_dir) or not os.listdir(discourse_md_dir):
                    raise HTTPException(404, "No markdown files generated from Discourse posts.")

  
                embed_file = os.path.join(tmpdir, "combined_embeddings.npz")
                embed_md_files([COURSE_MD_DIR, discourse_md_dir], embed_file)
                if not os.path.exists(embed_file) or os.path.getsize(embed_file) == 0:
                    raise HTTPException(500, "Embedding step failed or returned no data.")

                data = np.load(embed_file, allow_pickle=True)
                all_embeddings = data["embeddings"]
                all_metadata = data["metadata"]
                if all_embeddings is None or all_metadata is None or len(all_embeddings) == 0:
                    raise HTTPException(500, "No embeddings found for search.")

                
                query_emb = embed_text(question)
                if query_emb is None:
                    raise HTTPException(500, "Query embedding failed.")

                query_vector = np.array(query_emb)
                scores = np.dot(all_embeddings, query_vector)
                top_indices = scores.argsort()[-6:][::-1]
                context_chunks = [all_metadata[i] for i in top_indices if i < len(all_metadata)]
                if not context_chunks:
                    raise HTTPException(404, "No relevant context found for your query.")

                context_texts = [chunk.get("content", "") for chunk in context_chunks if chunk and chunk.get("content")]
                if not any(context_texts):
                    raise HTTPException(500, "Context chunks retrieved but had no usable content.")
                            
                answer = generate_answer(question, context_texts)
                links = [
                    Link(url=chunk["url"], text=chunk["content"][:200].strip() + "...")
                    for chunk in context_chunks if chunk.get("url")
                ]

                return ChatResponse(answer=answer, links=links)


    except asyncio.TimeoutError:
        raise HTTPException(504, "Request timeout")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Internal error: {str(e)}")
        
@app.get("/")
async def health_check():
    return {"status": "OK", "version": "1.0.0"}
