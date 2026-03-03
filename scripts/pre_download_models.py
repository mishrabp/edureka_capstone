
from sentence_transformers import SentenceTransformer
import os

def pre_download():
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    print(f"Pre-downloading embedding model: {model_name}...")
    SentenceTransformer(model_name)
    print("Model successfully downloaded and cached.")

if __name__ == "__main__":
    pre_download()
