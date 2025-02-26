# AI Tutor Project Setup and Use

This project sets up a chatbot using ChromaDB for vector storage and Large Language Model for processing responses.

## Prerequisites

- Python 3.7+
- Required dependencies (install via `requirements.txt`)
- Hugging Face API key
- Gemini API key
- ChromaDB
- Flask

## Setup Instructions

1. **Install Required dependencies**  
    Run following command,
    ```
    pip3 install -r requirements.txt
    ```
    If you get errors regarding modules not found while running the application install them with `pip3 install MODULE_NAME`.

2. **Add Hugging Face Token**  
   Open `get_embedding_function.py` and set your Hugging Face API key:
   ```python
   HF_API_KEY = "your_huggingface_api_key"
   ```

3. **Set Up Environment Variables**  
    Create a `.env` file in the root directory and include your Gemini API key:
    ```python
    GEMINI_API_KEY="your_gemini_api_key"
    ```

4. **Populate Database**  
    Run the following script to create a ChromaDB instance using `Resource Version 3.xlsx`:
    ```python
    python3 populate_database.py
    ```

5. **Run the Application**  
    Start the Flask server by executing:
    ```python
    python3 app.py
    ```

6. **Access the Chatbot**  
    Open your browser and go to:
    ```
    http://127.0.0.1:5000
    ```
    The chatbot should be up and running.

## Usage
Have a chat with the bot.
To start a new conversation, restart the server every time.

## Customization
To adjust the number of questions the chatbot asks, edit the following variables in `app.py`:
```
MIN_QUESTIONS = your_value
MAX_QUESTIONS = your_value
```

## License
This project is licensed under the MIT License.