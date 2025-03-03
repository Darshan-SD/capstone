from langchain_community.llms import Ollama

# Load Mistral 7B as Agent B (Learning Plan Generator)
llm_agent_b = Ollama(model="mistral")

def agent_b_followup(user_query):
    """
    Uses Mistral 7B to generate a follow-up question based on the user's learning request.
    Returns: A relevant follow-up question.
    """
    prompt = f"""
    You are an AI assistant that **helps users learn AI/ML** by asking **relevant follow-up questions**.

    🔹 **Rules:**
    - If a user asks **general AI/ML questions**, do NOT ask follow-ups.
    - If a user **wants to learn** a topic, ask a **follow-up question** to assess their experience.
    - The question should be **short, direct, and useful**.

    🔹 **Examples:**
    - "I want to learn deep learning." → "Do you have experience with Python and NumPy?"
    - "Can you guide me on reinforcement learning?" → "Have you worked with Markov Decision Processes before?"
    - "How should I start learning AI from scratch?" → "Do you have any prior programming experience?"
    
    User's request: "{user_query}"
    
    Generate only **one** follow-up question:
    """

    response = llm_agent_b.invoke(prompt).strip()
    return response

# 🚀 Test Cases
test_queries = [
    "I want to learn about transformers.",
    "Can you guide me on reinforcement learning?",
    "How should I start learning AI from scratch?",
    "I need a study plan for LLMs."
]

print("\n🔹 Agent B (Learning Plan Generator) Test Results:\n")
for query in test_queries:
    followup = agent_b_followup(query)
    print(f"🔹 Query: \"{query}\"\n✅ Follow-up Question: {followup}\n")