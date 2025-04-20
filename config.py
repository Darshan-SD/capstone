# config.py
from dotenv import load_dotenv
from langchain_community.llms import Ollama
from flask import Flask
from flask_session import Session
import redis
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

app.secret_key = os.getenv("FLASK_SECRET_KEY")
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')



# Constants
MIN_QUESTIONS = 1
MAX_QUESTIONS = 3

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
# user_session = {
#     "query": None,
#     "responses": [],
#     "questions": [],
#     "question_count": 0,
#     "scores": []
# }

# Session config for Redis
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = False
app.config["SESSION_REDIS"] = redis.Redis(host="localhost", port=6379, db=0)
app.config["SESSION_KEY_PREFIX"] = "session:" 

#Database config
#SECRET_KEY = os.getenv('SECRET_KEY')
# app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
# app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
# app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
# app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DB = os.getenv('MYSQL_DB')

Session(app)  # Initialize session extension