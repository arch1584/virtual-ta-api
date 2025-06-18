import os
import numpy as np
import requests
from app.utils import chunk_text, extract_images_from_md, get_image_description
from dotenv import load_dotenv
from InstructorEmbedding import INSTRUCTOR

load_dotenv()



model = INSTRUCTOR('hkunlp/instructor-large')

def embed_text(text: str) -> list:
    instruction = "Represent the text for retrieval:"
    try:
        emb = model.encode([[instruction, text]])[0]
        print("Text embedded successfully using InstructorEmbedding.")
        return emb.tolist()  # Convert numpy to list for consistency
    except Exception as e:
        print(f"InstructorEmbedding error: {e}")
        return None



def embed_md_files(md_dirs, out_file):
    embeddings = []
    metadata = []

    for md_dir in md_dirs:
        if not os.path.exists(md_dir):
            print(f"Directory not found: {md_dir}")
            continue

        for fname in os.listdir(md_dir):
            if not fname.endswith(".md"):
                continue

            full_path = os.path.join(md_dir, fname)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"Failed to read {full_path}: {e}")
                continue

            # Handle text chunks
            chunks = chunk_text(content)
            if not chunks:
                print(f"No text chunks extracted from {fname}")
                continue

            for chunk in chunks:
                emb = embed_text(chunk)
                if emb:
                    embeddings.append(emb)
                    metadata.append({
                        "file": fname,
                        "type": "text",
                        "content": chunk,
                        "source_dir": md_dir
                    })

            # Handle images
            images = extract_images_from_md(content)
            if not images:
                continue

            for img_url in images:
                description = get_image_description(img_url)
                if not description or description == "Image description not available":
                    continue
                emb = embed_text(description)
                if emb:
                    embeddings.append(emb)
                    metadata.append({
                        "file": fname,
                        "type": "image",
                        "content": description,
                        "source_dir": md_dir
                    })

    if not embeddings:
        raise ValueError("No embeddings were generated. Aborting save.")

    np.savez_compressed(out_file, embeddings=np.array(embeddings), metadata=metadata)
    print(f"Embeddings saved to {out_file}")
    return out_file