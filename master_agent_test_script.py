from langchain_community.llms import Ollama  # Updated import

# Load Mistral 7B as the Master Agent
llm_master = Ollama(model="mistral")

def classify_query(user_query):
    """
    Uses Mistral 7B to classify the query as 'A' (FAQ) or 'B' (Learning Plan).
    Returns: "A" or "B"
    """
    master_prompt = f"""
    You are an AI model trained to classify user queries into two categories:

    - "A" → The user is asking a **factual AI/ML question** (e.g., "What is deep learning?" or "Explain CNNs in ML.").
    - "B" → The user is **requesting a learning plan or structured guidance** (e.g., "I want to learn reinforcement learning" or "How should I start learning transformers?").

    🔹 **Examples**:
    - "What is a decision tree?" → **A**
    - "I want to learn about neural networks." → **B**
    - "Can you guide me on reinforcement learning?" → **B**
    - "How does CNN work?" → **A**
    - "How should I start learning AI from scratch?" → **B**

    Based on this, classify the following **user query**:
    "{user_query}"

    🔹 **Rules:**
    - If the query is a **simple factual AI/ML question**, return **only "A"**.
    - If the query **mentions learning, studying, or improving**, return **only "B"**.
    - Return **only "A" or "B"** with no extra text.
    """

    response = llm_master.invoke(master_prompt).strip()

    # Ensure only "A" or "B" is returned
    if response not in ["A", "B"]:
        response = "Unknown"

    return response

# 🚀 Test Cases
test_queries = [
    "What is deep learning?",
    "How does CNN work?",
    "I want to learn about transformers.",
    "Can you guide me on reinforcement learning?",
    "What is a decision tree?",
    "How should I start learning AI from scratch?",
    "I need a study plan for LLMs.",
    "Where should I start with AI research?"
]

print("\n🔹 Master Agent Classification Results:\n")
for query in test_queries:
    result = classify_query(query)
    print(f"🔹 Query: \"{query}\" → Classified as: {result}")