# config.py
from dotenv import load_dotenv
from langchain_community.llms import Ollama
from flask import Flask
import os

load_dotenv()

# Open Router Elements
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")
if OPEN_ROUTER_API_KEY is None:
    raise ValueError("OPEN_ROUTER_API_KEY not found in environment variables.")

OPEN_ROUTER_HEADERS = {
    "Authorization": f"Bearer {OPEN_ROUTER_API_KEY}",
    "Content-Type": "application/json",
}

OPEN_ROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def open_router_data(agent, prompt):
    model = "mistralai/mistral-7b-instruct:free"
    if agent == "master":
        model = "mistralai/mistral-7b-instruct:free"
    elif agent == "a":
        model = "mistralai/mistral-7b-instruct:free"
    elif agent == "b":
        model = "mistralai/mistral-7b-instruct:free"
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }

# Initialize Flask app (optional: or keep in app_test.py)
app = Flask(__name__)

# Constants
MIN_QUESTIONS = 3
MAX_QUESTIONS = 5

# Error messages
RETRY_ERROR = "Something went wrong with the servers. Please try again."
GENERAL_ERROR = "An error occurred. Please enter the query again or try reloading the page."

# LLMs
llm_master = Ollama(model="mistral")
llm_agent_a = Ollama(model="mistral")
llm_agent_b = Ollama(model="mistral")

# File paths
main_excel_file = "data/Resources Version 3.xlsx"
topic_ids_excel_file = "data/topic_ids_v3.xlsx"
user_level_ids_excel_file = "data/user_level_ids.xlsx"

# Excel columns
main_sheet = "main"
main_topic_ids_col = "Topic_ids"
main_user_level_col = "Difficulty Level"
main_chromadb_doc_id_col = "doc_id"

topicids_col = "key_name"
topicids_value_col = "value"

# Session storage
user_session = {
    "query": None,
    "responses": [],
    "questions": [],
    "question_count": 0,
    "scores": []
}