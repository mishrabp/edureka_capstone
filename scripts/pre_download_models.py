from sentence_transformers import SentenceTransformer
import os

def pre_download():
    # We save to a fixed local path inside the Docker image
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    save_path = "/app/model_cache"
    
    print(f"🚀 Pre-downloading and saving model: {model_name} to {save_path}...")
    
    # Download the model
    model = SentenceTransformer(model_name)
    
    # Save it locally so we can load it by path at runtime
    os.makedirs(save_path, exist_ok=True)
    model.save(save_path)
    
    print(f"✅ Model successfully saved to {save_path}")

if __name__ == "__main__":
    pre_download()
