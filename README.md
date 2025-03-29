# AI Tutor Project Setup and Use

This project sets up a AI tutor using ChromaDB for vector storage and Large Language Model for processing responses.

## Prerequisites

- Python 3.7+
- Required dependencies (install via `requirements.txt`)
- Hugging Face API key
- Ollama
- ChromaDB
- Flask

## To change the configuration of the app
- Visit `config.py` to change the local LLM, MIN_QUESTIONS, MAX_QUESTIONS, etc.

## Setup Instructions
First, make sure Ollama is running in the background with Mistral model installed on your system

1. **Install Required dependencies**  
    Run following command,
    ```
    pip3 install -r requirements.txt
    ```
    If you get errors regarding `modules not found` while running the application install them with `pip3 install MODULE_NAME`.

2. **Add Hugging Face Token**  
   Create a `.env` file in the root directory and include your Hugging Face API key:
   ```python
   HF_API_KEY = "your_huggingface_api_key"
   ```

3. **Populate Database**  
    Run the following script to create a ChromaDB instance using `Resource Version 3.xlsx`:
    ```python
    python3 populate_database.py
    ```

4. **Run the Application**  
    Start the Flask server by executing:
    ```python
    python3 app.py
    ```

5. **Access the Chatbot**  
    Open your browser and go to:
    ```
    http://127.0.0.1:5000
    ```
    The chatbot should be up and running.

Happy AI Learning :)