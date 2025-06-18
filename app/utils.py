import re
import os
import requests
import base64
import numpy as np
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import requests
import torch


processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")


load_dotenv()


def load_npz(file_path):
    """Load embeddings from a .npz file and return the embeddings array."""
    if not os.path.exists(file_path):
        print("NPZ file not found!")
        return None

    data = np.load(file_path, allow_pickle=True)
    embeddings = data.get('embeddings')
    
    if embeddings is not None and len(embeddings) > 0:
        print("Embeddings loaded successfully!\n")
        return embeddings
    else:
        print("Embeddings missing or empty in npz file.\n")
        return None

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

    print("Text chunked successfully!\n" if chunks else "Text chunking failed!\n")
    return chunks  # Always return a list


def extract_images_from_md(md_content):
    if not md_content:
        print("Markdown empty. Images fetching failed!\n")
        return []
    print("Images from markdown fetched successfully!\n")
    return re.findall(r'!\[.*?\]\((.*?)\)', md_content)




def get_image_description(image_url):
    try:
        raw_image = Image.open(requests.get(image_url, stream=True).raw).convert('RGB')
        inputs = processor(raw_image, return_tensors="pt")
        out = model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        print("Image caption generated using BLIP.")
        return caption
    except Exception as e:
        print(f"Image captioning failed: {e}")
        return "Image description not available"





def get_url_text(url: str, max_length: int = 3000) -> str:
    """
    Fetch and extract the main text content from a given URL.
    Truncates the result to `max_length` characters.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove scripts, styles, and nav elements
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        # Try to extract main content heuristically
        main = soup.find("main") or soup.body
        if not main:
            raise ValueError("Could not find main content in HTML")

        text = main.get_text(separator="\n", strip=True)
        print("URL text fetched successfully!\n")
        return text[:max_length]
    except Exception as e:
        raise RuntimeError(f"Failed to fetch or parse URL content: {e}")
