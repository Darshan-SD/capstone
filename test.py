import requests

API_KEY = "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"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

prompt = (
    "### MASTER CLASSIFICATION AGENT ###\n\n"
    "You are an AI assistant responsible for classifying user queries into one of three categories:\n\n"
    
    " **Category A (FAQ Agent)** → The user is asking a **factual AI/ML question**\n"
    "   - Example: 'What is deep learning?', 'Explain backpropagation.', 'What is the difference between CNN and RNN?'\n\n"

    " **Category B (Learning Plan Agent)** → The user wants to learn about AI/ML concepts and is requesting a **structured learning plan**\n"
    "   - Example: 'I want to learn transformers.', 'How do I start with machine learning?', 'Guide me on learning computer vision.'\n\n"

    " **Category GREET (Greeting/Non-AI Query)** → The user is greeting, making small talk, or entering an unrelated query\n"
    "   - Example: 'Hello!', 'How are you?', 'What's up?', 'Good morning!'\n"
    "   - **Response:** If a greeting is detected, respond with a polite message encouraging the user to ask something AI/ML-related.\n\n"
    
    "**IMPORTANT RULES:**\n"
    "1 Return only a JSON object with a single key 'category' and one of these values: 'A', 'B', or 'GREET'.\n"
    "2 If unsure, default to 'A' (FAQ) for specific AI/ML concept explanations or 'B' (Learning Plan) for general AI/ML learning requests.\n"
    "3 If the query is a greeting or off-topic, classify as 'GREET'.\n\n"

    "### Example Responses:\n"
    "- User Query: 'What is reinforcement learning?'\n"
    "  { \"category\": \"A\" }\n"
    "- User Query: 'I want to become an AI engineer.'\n"
    "  { \"category\": \"B\" }\n"
    "- User Query: 'Hey there!'\n"
    "  { \"category\": \"GREET\" }\n\n"
    
    f"User Query: \"what is supervised learning?\"\n"
    "### JSON Response (Only return this):"
    )

data = {
    "model": "mistralai/mistral-7b-instruct",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
}


response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

if response.status_code == 200:
    reply = response.json()
    print("Mistral-7B response:", reply["choices"][0]["message"]["content"])
else:
    print("Error:", response.status_code, response.text)
