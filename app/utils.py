import re
import os
import requests
import base64
import numpy as np
from dotenv import load_dotenv

load_dotenv()
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")
AIPIPE_BASE = "https://aipipe.org/openai/v1"

def load_npz(file_path):
    """Load embeddings from a .npz file and return the embeddings array."""
    data = np.load(file_path, allow_pickle=True)
    return data['embeddings']


def chunk_text(text, max_tokens=512):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len((current + sent).split()) > max_tokens:
            if current.strip():
                chunks.append(current.strip())
            current = sent
        else:
            current += " " + sent
    if current.strip():
        chunks.append(current.strip())
    return chunks

def extract_images_from_md(md_content):
    return re.findall(r'!\[.*?\]\((.*?)\)', md_content)

def get_image_description(image_base64_or_url):
    """Handle both base64 and URL images"""
    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Check if it's base64 or URL
    if image_base64_or_url.startswith(('http://', 'https://')):
        image_url = image_base64_or_url
    else:
        # It's base64, convert to data URL
        image_url = f"data:image/jpeg;base64,{image_base64_or_url}"
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail for a student to understand:"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]
    }

    try:
        response = requests.post(f"{AIPIPE_BASE}/chat/completions", headers=headers, json=data, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"Image captioning failed: {e}")
        return "Image description not available"
