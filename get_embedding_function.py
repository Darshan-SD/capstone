# from langchain_community.embeddings.ollama import OllamaEmbeddings
# from langchain_community.embeddings.bedrock import BedrockEmbeddings


# def get_embedding_function():
#     # embeddings = BedrockEmbeddings(
#     #     credentials_profile_name="default", region_name="us-east-1"
#     # )
#     embeddings = OllamaEmbeddings(model="nomic-embed-text")
#     return embeddings


from langchain_community.embeddings.huggingface import HuggingFaceInferenceAPIEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")

def get_embedding_function():
    print(f"API Key: {HF_API_KEY}")
    embeddings = HuggingFaceInferenceAPIEmbeddings(
        api_key=HF_API_KEY,
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return embeddings

# emb = get_embedding_function()
# print(f"Embedding test: {emb.embed_query('test sentence')}")

# import requests

# model_id = "sentence-transformers/all-MiniLM-L6-v2"

# api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
# headers = {"Authorization": f"Bearer {HF_API_KEY}"}

# def query(texts):
#     response = requests.post(api_url, headers=headers, json={"inputs": texts, "options":{"wait_for_model":True}})
#     return response.json()

# print(f"Query test: {query(['test sentence'])}")

