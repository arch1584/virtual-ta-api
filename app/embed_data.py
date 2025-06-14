import os
import numpy as np
import requests
from utils import chunk_text, extract_images_from_md, get_image_description
from dotenv import load_dotenv

load_dotenv()
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
AIPIPE_BASE = "https://aipipe.org/openai/v1"

def embed_text(text: str) -> list:
    if not text.strip():
        return None
        
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "input": text,
        "model": "text-embedding-ada-002"
    }
    try:
        response = requests.post(f"{AIPIPE_BASE}/embeddings", headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None



def embed_md_files(md_dirs, out_file):
    embeddings = []
    metadata = []
    for md_dir in md_dirs:
        for fname in os.listdir(md_dir):
            if not fname.endswith(".md"):
                continue
            full_path = os.path.join(md_dir, fname)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = chunk_text(content)
            for chunk in chunks:
                emb = embed_text(chunk)
                if emb is not None:
                    embeddings.append(emb)
                    metadata.append({"file": fname, "type": "text", "content": chunk, "source_dir": md_dir})
            images = extract_images_from_md(content)
            for img_url in images:
                description = get_image_description(img_url)
                emb = embed_text(description)
                if emb is not None:
                    embeddings.append(emb)
                    metadata.append({"file": fname, "type": "image", "content": description, "source_dir": md_dir})
    np.savez_compressed(out_file, embeddings=np.array(embeddings), metadata=metadata)

if __name__ == "__main__":
    embed_md_files(
        ["data/fetched_discourse/", "data/course_content_md/"],
        "data/embeddings/tds_embeddings.npz"
    )
