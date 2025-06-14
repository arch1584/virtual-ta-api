from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import base64
import asyncio
import numpy as np
from embed_data import embed_text
from utils import get_image_description
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    image: Optional[str] = None

class Link(BaseModel):
    url: str
    text: str

class ChatResponse(BaseModel):
    answer: str
    links: List[Link]

# Load embeddings at startup
discourse_data = np.load("data/embeddings/discourse_embeddings.npz", allow_pickle=True)
course_data = np.load("data/embeddings/course_content_embeddings.npz", allow_pickle=True)

def search_embeddings(query_vector, k=6):
    """Search both discourse and course embeddings"""
    all_embeddings = np.vstack([discourse_data["embeddings"], course_data["embeddings"]])
    all_metadata = np.concatenate([discourse_data["metadata"], course_data["metadata"]])
    
    # Cosine similarity
    scores = np.dot(all_embeddings, query_vector)
    top_indices = np.argsort(scores)[-k:][::-1]
    
    return [all_metadata[i] for i in top_indices]

@app.post("/api/", response_model=ChatResponse)
async def get_response(req: ChatRequest):
    try:
        # Add 30-second timeout
        async with asyncio.timeout(30):
            question = req.question
            
            # Handle image if provided
            if req.image:
                try:
                    # Decode base64 image and get description
                    image_data = base64.b64decode(req.image)
                    alt_text = get_image_description(req.image)  # Pass base64 string
                    question = f"Image description: {alt_text}\nQuestion: {question}"
                except Exception as e:
                    raise HTTPException(400, f"Image processing failed: {str(e)}")
            
            # Embed query and search
            query_vector = np.array(embed_text(question))
            context_chunks = search_embeddings(query_vector, k=6)
            
            # Generate simple response (you can enhance this)
            answer = f"Based on the context, here's the answer to: {question}"
            links = []
            
            # Extract links from context
            for chunk in context_chunks[:3]:  # Top 3 results
                if chunk.get("url"):
                    links.append({
                        "url": chunk["url"], 
                        "text": chunk["content"][:100] + "..."
                    })
            
            return ChatResponse(answer=answer, links=links)
            
    except asyncio.TimeoutError:
        raise HTTPException(504, "Request timeout")
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")

async def health_check():
    return {"status": "OK", "version": "1.0.0"}
