from langchain_community.llms import Ollama

# Load Mistral 7B as Agent A (FAQ Handler)
llm_agent_a = Ollama(model="mistral")

def agent_a_answer(user_query):
    """
    Uses Mistral 7B to answer general AI/ML questions concisely.
    Returns: Short factual answer.
    """
    prompt = f"""
    You are an AI assistant that provides **concise and factual answers** to AI/ML questions.

    🔹 **Examples:**
    - "What is deep learning?" → "Deep learning is a subset of ML that uses neural networks to model complex patterns."
    - "How does CNN work?" → "A Convolutional Neural Network (CNN) processes images using layers that detect patterns like edges and textures."
    - "What is overfitting?" → "Overfitting occurs when a model learns noise instead of general patterns, leading to poor generalization."

    Answer this question concisely: "{user_query}"
    """

    response = llm_agent_a.invoke(prompt).strip()
    return response

# 🚀 Test Cases
test_queries = [
    "What is deep learning?",
    "How does CNN work?",
    "What is a decision tree?",
    "What is overfitting in machine learning?"
]

print("\n🔹 Agent A (FAQ Handler) Test Results:\n")
for query in test_queries:
    answer = agent_a_answer(query)
    print(f"🔹 Query: \"{query}\"\n✅ Answer: {answer}\n")