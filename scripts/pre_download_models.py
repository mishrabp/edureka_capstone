
from sentence_transformers import SentenceTransformer
import os

def pre_download():
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    cache_folder = os.getenv("HF_HOME", "/home/user/.cache")
    print(f"Pre-downloading embedding model: {model_name} to {cache_folder}...")
    SentenceTransformer(model_name, cache_folder=cache_folder)
    print("Model successfully downloaded and cached.")

if __name__ == "__main__":
    pre_download()
