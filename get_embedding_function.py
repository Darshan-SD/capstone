import os
import torch
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def log(msg: str):
    """Helper function to print messages with timestamps."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_embedding_function():
    from langchain_huggingface import HuggingFaceEmbeddings
    
    model_name = "sentence-transformers/all-mpnet-base-v2"  
    # try "all-MiniLM-L6-v2" if you need faster/lighter

    # Auto-detect best device
    if torch.cuda.is_available():
        device = "cuda"   # NVIDIA GPU (RTX A5000)
    elif torch.backends.mps.is_available():
        device = "mps"    # Apple Silicon GPU
    else:
        device = "cpu"

    log(f"Using device: {device}")

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device}
    )
    return embeddings


if __name__ == "__main__":
    log("Loading embedding model...")
    embeddings = get_embedding_function()

    # --- Single query test ---
    text = "Hello, cross-platform embeddings!"
    log("Starting single query embedding...")
    start = time.time()
    vector = embeddings.embed_query(text)
    end = time.time()
    log(f"Single query took {end - start:.4f} seconds")
    print(f"Vector length: {len(vector)} | First 5 values: {vector[:5]}")

    # --- Batch test ---
    docs = ["This is a test sentence." for _ in range(1000)]
    log("Starting batch embedding of 1000 documents...")
    start = time.time()
    vectors = embeddings.embed_documents(docs)
    end = time.time()
    log(f"Batch embedding took {end - start:.4f} seconds")
    print(f"Embedded {len(vectors)} vectors of size {len(vectors[0])}")

