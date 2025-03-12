from flask import Flask, request, jsonify, render_template
from langchain_community.llms import Ollama
import os
import json
import logging
import pandas as pd
from query_data import query_rag
from dotenv import load_dotenv
import re  # Import regex for extracting numbers
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)
load_dotenv()


MIN_QUESTIONS = 2
MAX_QUESTIONS = 2 # Agent B decides dynamically how many to ask

# Load LLM models
llm_master = Ollama(model="mistral")  # Master Agent
llm_agent_a = Ollama(model="mistral")  # FAQ Handler (Agent A)
llm_agent_b = Ollama(model="mistral")  # Learning Plan Generator (Agent B)

# Excel file paths
main_excel_file = "Resources Version 3.xlsx"
topic_ids_excel_file = "topic_ids_v3.xlsx"
user_level_ids_excel_file = "user_level_ids.xlsx"

# Excel columns
main_sheet = "main"
main_topic_ids_col = "Topic_ids"
main_user_level_col = "Difficulty Level"
main_chromadb_doc_id_col = "doc_id"

topicids_col = "key_name"
topicids_value_col = "value"

# Session storage
user_session = {"query": None, "responses": [], "questions": [], "question_count": 0, "scores": []}

### 1️ Master Agent: Classify Query ###
def classify_query(user_query):
    """
    Master Agent: Determines if the query goes to Agent A (FAQ), Agent B (Learning Plan), 
    or if the user is greeting (redirecting them to AI/ML questions).
    Returns: "A", "B", or "GREET"
    """
    master_prompt = (
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
    
    f"User Query: \"{user_query}\"\n"
    "### JSON Response (Only return this):"
    )

    # Invoke LLM with lower temperature
    response = llm_master.invoke(master_prompt).strip()
    
    # Debugging logs
    logging.info(f"Master Agent raw response: '{response}'")
    
    try:
        response_data = json.loads(response)
        classification = response_data.get("category", "Unknown")
    except json.JSONDecodeError:
        classification = "Unknown"

    # Handling the unknown classification
    if classification == "Unknown":
        logging.warning(f"Master Agent struggled to classify: '{user_query}'. Retrying with a refined prompt...")
        
        retry_prompt = (
        "Classify the user query into one of the following:\n"
        "- \"A\": Factual AI/ML question (e.g., \"What is deep learning?\")\n"
        "- \"B\": Learning request (e.g., \"I want to learn transformers.\")\n"
        "- \"GREET\": Greeting or non-AI/ML conversation (e.g., \"Hello!\", \"How are you?\")\n\n"
        
        "**STRICT RULE:** Return ONLY a JSON object like this:\n"
        "{ \"category\": \"A\" } or { \"category\": \"B\" } or { \"category\": \"GREET\" }\n\n"

        f"User Query: \"{user_query}\"\n"
        "### Final Answer (Only return JSON):"
        )

        response = llm_master.invoke(retry_prompt).strip()
        logging.info(f"Master Agent retry response: '{response}'")
        
        try:
            response_data = json.loads(response)
            classification = response_data.get("category", "Unknown")
        except json.JSONDecodeError:
            classification = "Unknown"

    # If the query is a greeting, provide a polite redirection message
    if classification == "GREET":
        logging.info("Master Agent detected a greeting. Redirecting user to AI/ML domain.")
        return "GREET"

    logging.info(f"Master Agent classified the query as: {classification}")
    return classification

### 2️ Agent A: Provide Direct Answer ###
def agent_a_answer(user_query):
    """
    Agent A (FAQ Handler): Provides direct AI/ML answers without RAG.
    """
    # prompt = f"Provide a concise, factual answer to this user query and stick to  AI/ML field only: {user_query}"
    prompt = f"""
    You are an AI FAQ assistant specialized in answering technical questions related to Artificial Intelligence (AI) and Machine Learning (ML).
    Your task is to provide **concise, precise, and factually accurate** responses to user queries.

    **Guidelines:**
    - Stick strictly to AI/ML topics and ignore unrelated queries.
    - Keep responses **direct, informative, and to the point** (ideally within 2-3 sentences).
    - If multiple interpretations exist, pick the most **commonly accepted** explanation.
    - Do **not** provide speculative, opinion-based, or general advice beyond AI/ML.
    - Use clear and professional language suitable for technical users.
    - If the query is **ambiguous**, clarify it instead of making assumptions.

    ### **Few-Shot Examples:**
    **User Query:** What is the difference between supervised and unsupervised learning?
    **Response:** Supervised learning involves training a model on labeled data, meaning each input has a corresponding correct output. Unsupervised learning, on the other hand, deals with unlabeled data, where the model identifies patterns and structures within the data without explicit guidance.

    **User Query:** What is backpropagation in neural networks?
    **Response:** Backpropagation is an optimization algorithm used to train neural networks. It calculates the gradient of the loss function with respect to each weight by using the chain rule, enabling the model to adjust weights iteratively to minimize error.

    **User Query:** Can you explain the role of activation functions in deep learning?
    **Response:** Activation functions introduce non-linearity into neural networks, enabling them to learn complex patterns. Common activation functions include ReLU, Sigmoid, and Tanh, each serving different purposes based on the task and network architecture.

    **User Query:** How does a decision tree work in machine learning?
    **Response:** A decision tree is a flowchart-like model that splits data into branches based on feature values. It recursively partitions data into subsets until it reaches a decision, making it useful for classification and regression tasks.

    **User Query:** What is the role of a loss function in machine learning?
    **Response:** A loss function quantifies the difference between predicted and actual values in a model. It helps in optimizing the model by guiding adjustments to its parameters to minimize prediction errors.

    ---

    **Now, respond to the following user query based on the provided guidelines and examples:**
    **User Query:** {user_query}
    **Your Response:**
    """
    response = llm_agent_a.invoke(prompt).strip()
    logging.info(f"Agent A provided response: {response}")
    return response

### 3️ Agent B: Generate Follow-up Questions ###
def agent_b_followup(context):
    """
    Agent B generates one follow-up question at a time based on previous responses.
    It dynamically decides whether more questions are needed.
    """
    # prompt = f"""
    # The user wants to learn AI/ML. Based on their responses so far, generate the next logical follow-up question.

    # **RULES:**
    # - Consider the context and prior responses.
    # - Ensure the follow-up question logically continues the conversation.
    # - Do NOT repeat previous questions.
    # - Stay within the limit of {MAX_QUESTIONS} total follow-ups.
    
    # User Responses:
    # {user_responses}

    # **Final Output:** Return only the next follow-up question.
    # """

    prompt = (
        f"You are an expert in generating concise, targeted questions to assess a user's current knowledge in Artificial Intelligence and Machine Learning (AI/ML). "
        "Your role is to engage in natural, conversational interactions while:\n"
        "- Evaluating user needs and knowledge level.\n"
        "- Understand how long user is willing to spend learning.\n"
        "- Recommending appropriate learning resources.\n"
        "- Explaining concepts clearly.\n"
        "- Encouraging and motivating the user.\n\n"
        
        "### STRICT RULES:\n"
        "- Do not ask user direct questions what user already wants to know. For example, if user want to learn about Decision trees, do not ask 'Can you tell me what is Decision tree?'. But try to ask about any experience, programming knowledge, how much time the user have to learn and other related things.\n"
        "- Stay on topic; DO NOT change the discussion to unrelated subjects.\n"
        "- If the user is vague or uncertain (e.g., 'I don't know' or 'I'm not sure'), ask clarifying questions within the SAME topic.\n"
        "- Ensure each follow-up question builds upon the user's last clear response.\n"
        "- Avoid repeating previously asked questions.\n"
        "- Your response must be in JSON format.\n\n"
        
        "### RESPONSE FORMAT:\n"
        "You must return the response in the following JSON format:\n"
        "{\n"
        '  "question": "Your generated follow-up question based on the conversation so far."\n'
        "}\n\n"
        
        "### Example Conversations:\n\n"
        
        "**Example 1:**\n"
        "User: I want to learn Machine Learning.\n"
        "Assistant: Do you have hands-on experience in this field?\n"
        "User: I know a bit about it but never implemented any projects.\n"
        "Assistant: That's a good start! What's your main goal with Machine Learning? (Data Science, Web Development, General Programming, Scripting/Automation, Game Development, etc.)\n"
        "User: I want to get into Data Science.\n"
        "Assistant: I see! That requires programming skills. How comfortable are you with Python?\n"
        "User: I know the basics of Python, such as loops, functions, and data structures.\n"
        "Assistant: Great! Data Science involves a lot of math. Are you familiar with Linear Algebra and Statistics?\n"
        "User: I studied them in college but need a refresher.\n"
        "Assistant: Perfect! How many hours per day/week can you dedicate to studying Machine Learning?\n"
        "User: I can dedicate 2-3 hours daily.\n\n"
        
        "**Example 2:**\n"
        "User: I want to learn math concepts for AI.\n"
        "Assistant: Do you have any prior experience in AI or ML?\n"
        "User: Yes, but only classification and regression.\n"
        "Assistant: That's a good start! What specific math concepts are you interested in learning?\n"
        "User: Matrix operations and optimization algorithms.\n"
        "Assistant: Great! Since you have experience, I assume you know Python. How comfortable are you with it?\n"
        "User: I am comfortable with Python and have used it for data analysis.\n"
        "Assistant: What is your availability for studying math concepts for AI?\n"
        "User: As much as it requires.\n\n"
        
        f"Now, generate only ONE follow-up question based on the following conversation/query:\n{context}\n DO NOT REPEAT QUESTIONS.\n Respond in JSON format"
    )
    logging.info(f"\n\n\nAgent B follow-up prompt: {prompt}\n\n\n")
    response = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Agent B generated follow-up: {response}\n\n\n")
    # return response

    if "```" in response:
        response = response.split("```json")[1].split("```")[0].strip()
        
    response = json.loads(response)["question"]
    logging.info("Generated question: %s", response)
    return response


### 4️ Agent B: Score User Responses ###
def agent_b_score_response(response, question):
    """
    Scores a user's response based on depth, correctness, and relevance.
    Also determines whether another question is needed (within limits).
    """
    prompt = f"""
    Evaluate this user response in relation to the follow-up question in AI/ML.

    **Follow-up Question:** "{question}"
    **User Response:** "{response}"

    **TASKS:**
    1. Score the response on a scale from 0 to 5:
        - 0: No relevant information.
        - 5: Excellent response.
    
    2. Decide if another follow-up question is needed.
       - Consider if the response was unclear, vague, or missing important details.
       - If another question is needed, return "Yes".
       - If no more questions are needed, return "No".

    **Final Output (JSON format):**
    {{
      "score": X,
      "reasoning": "Brief explanation of score",
      "more_questions_needed": "Yes" or "No"
    }}
    """
    logging.info(f"\n\n\nScoring User Prompt: {prompt}\n\n\n")
    logging.info(f"\n\n\nUser Response with Question: {response, question}\n\n\n")
    result = llm_agent_b.invoke(prompt).strip()
    result_data = json.loads(result)

    logging.info(f"Scored Response: {result_data}")
    return result_data["score"], result_data["reasoning"], result_data["more_questions_needed"]

### 5️ Read Topic IDs from Excel ###
def get_topic_ids():
    df = pd.read_excel(topic_ids_excel_file, sheet_name="topic_ids")
    return dict(zip(df[topicids_col], df[topicids_value_col]))

### 6️ Find Relevant Topic IDs ###
def find_relevant_topic_ids(summary):
    topic_dict = get_topic_ids()
    topics_str = "\n".join([f"{topic}: {topic_id}" for topic, topic_id in topic_dict.items()])
    prompt = f"""
    Given the AI/ML-related summary:
    "{summary}"
    
    Here are topics and their IDs:
    {topics_str}

    Identify the most relevant topic IDs.

    **STRICT RULES:**
    - Return ONLY the topic IDs as a comma-separated list of numbers.
    - Do NOT include topic names or extra text.
    - Example Output: `12,14,20`
    """
    # response = llm_agent_b.invoke(prompt).strip()
    # logging.info(f"relevant topic ids: {response}")
    # return list(map(int, response.split(","))) if response else []
    response = llm_agent_b.invoke(prompt).strip()
    
    if not response:
        logging.warning("No topic IDs identified from the response.")
        return []

    try:
        # Extract only numbers using regex
        topic_ids = list(map(int, re.findall(r"\d+", response)))
        logging.info(f"Relevant topic IDs: {topic_ids}")
        return topic_ids
    except ValueError as e:
        logging.error(f"Failed to parse topic IDs from response: {response}. Error: {e}")
        return []

### 7️ Read User Level IDs from Excel ###
def get_user_level_ids():
    df = pd.read_excel(user_level_ids_excel_file, sheet_name="user_level_ids")
    return dict(zip(df["User Level"], df["ID"]))

### 8 Find User Level ID ###
def find_relevant_user_level_ids(user_level):
    user_level_dict = get_user_level_ids()
    levels_str = "\n".join([f"{level}: {level_id}" for level, level_id in user_level_dict.items()])
    
    prompt = f"""
    Given is the user level:
    "{user_level}"
    Here are user levels and their IDs:
    {levels_str}

    Identify the most relevant user level ID.
    
    **STRICT RULE:**
    - Return ONLY the ID as a single number.
    - DO NOT include any extra text.

    Example Output: `2`
    """

    response = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Relevant User Level id: {response}")

    # Extract only the first number from the response
    match = re.search(r"\d+", response)
    if match:
        user_level = int(match.group(0))
        if user_level not in [1, 2, 3]:  # Ensure valid level
            logging.warning(f"Unexpected level {user_level}, defaulting to Beginner (1).")
            return 1
        return user_level
        # return int(match.group(0))  # Convert extracted number to int

    logging.error("Could not extract a valid user level ID.")
    return None  # Return None if no valid ID found

### 9 Filter Relevant Resources ###
# def filter_records_by_topics_and_user_level(relevant_topic_ids, user_level_id):
#     df = pd.read_excel(main_excel_file, sheet_name=main_sheet)
#     df[main_topic_ids_col] = df[main_topic_ids_col].apply(lambda x: [int(i) for i in str(x).split(',')])
#     df[main_user_level_col] = df[main_user_level_col].apply(lambda x: [int(i) for i in str(x).split(',')])

#     filtered_df = df[
#         df[main_topic_ids_col].apply(lambda record: any(num in record for num in relevant_topic_ids)) &
#         df[main_user_level_col].apply(lambda record: user_level_id in record)
#     ]
#     return filtered_df[main_chromadb_doc_id_col].values.tolist()
def filter_records_by_topics_and_user_level(relevant_topic_ids, user_level_id):
    df = pd.read_excel(main_excel_file, sheet_name=main_sheet)

    # Convert stored IDs to proper format
    df[main_topic_ids_col] = df[main_topic_ids_col].apply(
        lambda x: [int(i.strip()) for i in str(x).split(',') if i.strip().isdigit()]
    )
    df[main_user_level_col] = df[main_user_level_col].apply(
        lambda x: [int(i.strip()) for i in str(x).split(',') if i.strip().isdigit()]
    )

    print(f"Relevant Topic IDs: {relevant_topic_ids}")
    print(f"User Level ID: {user_level_id}")
    print(df[[main_topic_ids_col, main_user_level_col]].head())  # Print column data for debugging

    # Apply filtering
    filtered_df = df[
        df[main_topic_ids_col].apply(lambda record: any(num in record for num in relevant_topic_ids)) &
        df[main_user_level_col].apply(lambda record: user_level_id in record)
    ]

    print(f"Filtered {len(filtered_df)} documents.", flush=True)  # Ensure immediate output
    sys.stdout.flush()  # Force printing


    return filtered_df[main_chromadb_doc_id_col].values.tolist()


### Extract Key Elements for RAG ###
def extract_key_elements(summary, user_level):
    prompt = f"""
    Extract the key AI/ML topics from this summary:
    "{summary}"
    Include the user's level: {user_level}.
    Provide only the key elements as a comma-separated list.
    """
    return llm_agent_b.invoke(prompt).strip().split(", ")

### Summarizing user response ###
def agent_b_summarize_learning(responses, user_availability):
    # """
    # Summarizes what the user wants to learn based on all responses.
    # """
    # prompt = f"""
    # You are an AI assistant responsible for summarizing a user's learning goals in AI/ML.
    
    # ### TASK:
    # - Analyze the provided user responses and identify key learning objectives.
    # - Extract specific topics the user is interested in.
    # - Capture any relevant programming skills, prior experience, and learning preferences.
    # - If the user mentions a **specific goal** (e.g., "I want to become a data scientist"), **include it** in the summary.
    # - Ensure the summary is **concise, structured, and informative**.
    
    # ### STRICT RULES:
    # - Focus **only** on AI/ML-related learning preferences.
    # - Do **not** add extra commentary or assumptions beyond what the user stated.
    # - If the user responses lack enough detail, return **"The user wants to learn AI/ML but did not specify details."**
    # - Format the summary as a **single structured sentence**.

    # ### EXAMPLES:
    # #### Example 1:
    # **User Responses:**
    # - "I want to learn about deep learning."
    # - "I have some experience with Python."
    # - "I am interested in computer vision."
    
    # **Summary Output:**
    # "The user wants to learn deep learning and computer vision, has some experience with Python, and aims to expand their AI/ML knowledge."

    # #### Example 2:
    # **User Responses:**
    # - "I want to learn AI."
    # - "I'm not sure where to start."
    
    # **Summary Output:**
    # "The user wants to learn AI but has not specified a starting point."

    # #### Example 3:
    # **User Responses:**
    # - "I want to become a machine learning engineer."
    # - "I am familiar with linear regression but want to explore deep learning."
    # - "I have intermediate Python skills and know basic statistics."
    
    # **Summary Output:**
    # "The user wants to become a machine learning engineer, has intermediate Python skills, understands basic statistics, and wants to explore deep learning beyond linear regression."

    # ---
    
    # ### USER RESPONSES:
    # {responses}

    # ### USER AVAILABILTY
    # {user_availability}

    # ### FINAL SUMMARY OUTPUT:
    # """
    """
    Summarizes what the user wants to learn based on all responses, including availability.
    """
    prompt = f"""
    You are an AI assistant responsible for summarizing a user's learning goals in AI/ML.
    
    ### TASK:
    - Analyze the provided user responses and identify key learning objectives.
    - Extract specific AI/ML topics the user is interested in.
    - Capture relevant programming skills, prior experience, and learning preferences.
    - If the user mentions a **specific goal** (e.g., "I want to become a data scientist"), **include it** in the summary.
    - Incorporate the **user’s availability** into the summary naturally at the end.
    - Ensure the summary is **concise, structured, and informative**.

    ### STRICT RULES:
    - Focus **only** on AI/ML-related learning preferences.
    - Do **not** add extra commentary or assumptions beyond what the user stated.
    - Do **not** speculate on availability (e.g., "The user has limited time" → instead, use exact availability like "1 month").
    - If the user responses lack enough detail, return **"The user wants to learn AI/ML but did not specify details."**
    - Format the summary as a **single structured sentence**, ensuring readability.

    ### EXAMPLES:
    #### Example 1:
    **User Responses:**
    - "I want to learn about deep learning."
    - "I have some experience with Python."
    - "I am interested in computer vision."
    **User Availability:** "I have 2 months."

    **Summary Output:**
    "The user wants to learn deep learning and computer vision, has some experience with Python, and aims to expand their AI/ML knowledge within 2 months."

    #### Example 2:
    **User Responses:**
    - "I want to learn AI."
    - "I'm not sure where to start."
    **User Availability:** "I can dedicate 4 weeks."

    **Summary Output:**
    "The user wants to learn AI but has not specified a starting point and has 4 weeks available for learning."

    #### Example 3:
    **User Responses:**
    - "I want to become a machine learning engineer."
    - "I am familiar with linear regression but want to explore deep learning."
    - "I have intermediate Python skills and know basic statistics."
    **User Availability:** "I have only 1 month."

    **Summary Output:**
    "The user wants to become a machine learning engineer, has intermediate Python skills, understands basic statistics, and wants to explore deep learning beyond linear regression within 1 month."

    ---
    
    ### USER RESPONSES:
    {responses}

    ### USER AVAILABILITY:
    {user_availability}

    ### FINAL SUMMARY OUTPUT:
    """

    summary = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Generated User Learning Summary: {summary}")
    return summary

### extracting key elements ###
def agent_b_extract_key_elements(summary,user_level):
   
    # """
    # Extracts key AI/ML topics from the user’s learning summary and includes the user level.
    # """
    # prompt = f"""
    # You are an AI model tasked with extracting key AI/ML-related topics from a user's learning summary. 

    # ### TASK:
    # - Identify important AI/ML concepts, skills, and tools mentioned in the summary.
    # - Extract **only** relevant keywords (e.g., "Neural Networks", "Deep Learning", "Python", "Statistics").
    # - Include the user's proficiency level **at the end** of the list.

    # ### STRICT RULES:
    # - Extract **only AI/ML-related** keywords (no extra words or explanations).
    # - Ensure the extracted topics are **comma-separated**.
    # - At the end of the list, **append the user level**.
    # - Do **not** generate full sentences—only the formatted list of keywords.

    # ### EXAMPLES:

    # #### Example 1:
    # **Input Summary:**
    # "The user wants to become a machine learning engineer, has intermediate Python skills, understands basic statistics, and wants to explore deep learning beyond linear regression."
    
    # **User Level:** Beginner

    # **Expected Output:**
    # machine learning, python, statistics, deep learning, linear regression, beginner

    # #### Example 2:
    # **Input Summary:**
    # "The user is interested in reinforcement learning, has advanced Python experience, knows probability theory, and wants to improve deep learning fundamentals."
    
    # **User Level:** Advanced

    # **Expected Output:**
    # reinforcement learning, python, probability theory, deep learning, advanced

    # ----

    # ### USER INPUT:
    # **Summary:** "{summary}"
    # **User Level:** {user_level}

    # ### FINAL OUTPUT FORMAT:
    # - Return only a comma-separated list of key topics, followed by the user level.
    # """
    """
    Extracts key AI/ML topics from the user’s learning summary and includes the user level.
    """
    prompt = f"""
    You are an AI model tasked with extracting key AI/ML-related topics from a user's learning summary. 

    ### TASK:
    - Identify important AI/ML concepts, skills, and tools mentioned in the summary.
    - Extract **only** relevant keywords (e.g., "Neural Networks", "Deep Learning", "Python", "Statistics").
    - **STRICTLY use the provided user level, do not infer your own.**
    - Ensure that the extracted topics are **directly from the summary**.
    - At the end of the list, **append the user level exactly as provided**.

    ### STRICT RULES:
    - Extract **only AI/ML-related** keywords (no extra words or explanations).
    - Ensure the extracted topics are **comma-separated**.
    - **DO NOT guess the user level**—always use **"{user_level}"** at the end.
    - Do **not** generate full sentences—only the formatted list of keywords.

    ### EXAMPLES:

    #### Example 1:
    **Input Summary:**
    "The user wants to become a machine learning engineer, has intermediate Python skills, understands basic statistics, and wants to explore deep learning beyond linear regression."
    
    **User Level:** Beginner

    **Expected Output:**
    machine learning, python, statistics, deep learning, linear regression, beginner

    #### Example 2:
    **Input Summary:**
    "The user is interested in reinforcement learning, has advanced Python experience, knows probability theory, and wants to improve deep learning fundamentals."
    
    **User Level:** Advanced

    **Expected Output:**
    reinforcement learning, python, probability theory, deep learning, advanced

    #### Example 3 (FORCING USER LEVEL CORRECTLY):
    **Input Summary:**
    "The user has no prior experience working with labeled datasets, is open to gaining practical experience in supervised learning through a project using labeled data, and aims to do so within 2 weeks."
    
    **User Level:** Intermediate

    **Expected Output:**
    supervised learning, labeled data, intermediate

    ----

    ### USER INPUT:
    **Summary:** "{summary}"
    **User Level (MUST BE INCLUDED AS IS):** {user_level}

    ### FINAL OUTPUT FORMAT:
    - Return only a comma-separated list of key topics, followed by the exact user level: **"{user_level}"**.
    """

    key_elements_response = llm_agent_b.invoke(prompt).strip()
    key_elements = key_elements_response.split(", ")  # Convert response into a list

    logging.info(f"Extracted Key Elements: {key_elements}")
    return key_elements

def respond_greeting(user_query):
    logging.info("Master Agent detected a greeting. Generating a dynamic greeting response.")

    greeting_prompt = (
    "You are an AI assistant responding to a greeting message.\n\n"
    "**Objective:**\n"
    "- Greet the user warmly and naturally.\n"
    "- Encourage them to ask a question related to AI or Machine Learning.\n"
    "- Suggest AI/ML topics they might find interesting.\n\n"

    "**Response Style:**\n"
    "- Friendly and engaging.\n"
    "- Keep the response under 50 words.\n\n"

    "### Example Responses:\n"
    "- 'Hello! Hope you're having a great day. If you're curious about AI, I can help! Want to learn about deep learning or natural language processing?'\n"
    "- 'Hey there! I’d love to chat about AI and ML. What aspect of artificial intelligence interests you the most today?'\n"
    "- 'Hi! It’s great to hear from you. If you're looking to explore AI, we can discuss topics like computer vision, neural networks, or ethical AI. What interests you?'\n\n"

    f"User Message: \"{user_query}\"\n"
    "### Generate a friendly response:"
    )

    greeting_response = llm_master.invoke(greeting_prompt).strip()
    logging.info(f"Greeting response generated: '{greeting_response}'")

    return greeting_response

def generate_availability_question():
    """
    Uses the LLM to dynamically generate a question about the user's availability.
    """
    prompt = """
    You are an AI conversation assistant guiding a user in learning AI/ML.
    
    ### TASK:
    - Generate a **natural, engaging** follow-up question to ask about the user's availability.
    - Ensure the question sounds **smooth and conversational**, rather than robotic.
    - The question should be **short** and **clear**, making it easy for the user to respond.
    
    ### EXAMPLES:
    - How much time can you dedicate for learning? (e.g., 2 weeks, 1 month, 3 months)
    - Before we build your learning plan, could you share how much time you're planning to invest in learning?
    - What’s your learning timeline? Are you looking for something short-term (a few weeks) or longer?
    - To personalize your learning path, could you tell me how much time you can commit each week?
    
    ### STRICT RULES:
    - **Do NOT** include long explanations or context—just return the question.
    - The response should be a **single sentence** in proper conversational English.
    - **Do NOT** assume any user preferences—let them specify their own time commitment.
    
    ### FINAL OUTPUT:
    Generate one availability-related question.
    """

    question = llm_agent_b.invoke(prompt).strip()
    question = re.sub(r'^"(.*)"$', r'\1', question)  
    logging.info(f"Generated Availability Question: {question}")
    return question

# Session storage (Resets when a new query is received)
user_session = {}

### Flask Routes ###
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    user_query = data.get("input")
    logging.info(f"Received user input: {user_query}")

    if not user_query:
        logging.error("No input received from user.")
        return jsonify({"error": "Please enter a query."}), 400

    # If a session is ongoing, use the same agent (Agent A or B)
    if "assigned_agent" in user_session:
        logging.info(f"Continuing session with Agent {user_session['assigned_agent']}.")
        return submit_response(user_query)
    
    # Reset session only when a new query is entered after a completed conversation
    if user_session.get("conversation_ended", False):
        logging.info("New query detected. Resetting session...")
        user_session.clear()
    
    # Step 1: Classify the query (Master Agent)
    classification = classify_query(user_query)
    logging.info(f"Master Agent classified the query as: {classification}")
    
    user_session.clear()
    user_session["conversation_ended"] = False  # Ensure conversation tracking resets
    
    if classification == "A":
        user_session["assigned_agent"] = "A"  # Store the assigned agent: A
        answer = agent_a_answer(user_query)
        return final_result(agent="A", answer=answer) 
        # return jsonify({"result": f"✅ Agent A: {answer}"})

    elif classification == "B":
        user_session["assigned_agent"] = "B"  # Store the assigned agent: B
        followup_question = agent_b_followup(user_query)  # Returns ONE question

        logging.info(f"Agent B generated follow-up question: {followup_question}")  # Fixed Logging

        user_session.update({
            "query": user_query,
            "responses": [],
            "questions": [followup_question],  # Store the question as a list
            "question_count": 1,  # Start with 1 question (adjust dynamically later)
            "scores": []
        })

        return jsonify({"question": followup_question, "clear_input": True})  # Fixed response format
    
    elif classification == "GREET":
        answer = respond_greeting(user_query)
        return jsonify({
            "final_response": False,
            "greeting": True,
            "result": f"{answer}"})

    else:
        logging.error(f"Unexpected classification result: {classification}")
        return jsonify({"error": "Failed to classify the query. Please try again."}), 500

@app.route("/submit_response", methods=["POST"])
def submit_response(user_response):
    data = request.json
    # user_response = data.get("response")
    question_index = data.get("question_index", 0)  #Ensure it defaults to 0 if missing

    if question_index is None:
        logging.error("Missing question_index in request.")
        return jsonify({"error": "Invalid request: question_index is missing."}), 400

    # Ensure the session has an assigned agent
    assigned_agent = user_session.get("assigned_agent")
    if not assigned_agent:
        logging.error("Error: No assigned agent found in session.")
        return jsonify({"error": "Session error. Please restart your query."}), 500

    logging.info(f"Processing response using Agent {assigned_agent}.")

    # Ensure `scores` exists before accessing it
    if "scores" not in user_session:
        user_session["scores"] = []

    # Ensure Agent B handles its own responses
    if assigned_agent == "B":
        if user_session.get("availability", False):
            user_session["user_availability"] = user_response
            user_session["availability"] = False 
            logging.info(f"User Availability Recorded: {user_response}")  
            return final_result(agent="B")

        if question_index >= len(user_session["questions"]):
            return jsonify({"error": "Invalid question index."}), 400

        question = user_session["questions"][question_index]
        logging.info(f"Received user response: {user_response}")
        # if not user_session.get("awaiting_availability", False):
        score, reasoning, more_questions_needed = agent_b_score_response(user_response, question)

        user_session["responses"].append(user_response)
        user_session["scores"].append({"response": user_response, "score": score, "reasoning": reasoning})

        logging.info(f"User Session: {user_session}")

        # If max questions reached or no more questions needed → Final Response
        if len(user_session["responses"]) >= MAX_QUESTIONS or more_questions_needed == "No":
            if "availability" not in user_session:
                # next_question = "Before we generate your learning plan, how much time can you dedicate to learning AI/ML? (e.g., 2 weeks, 1 month, 3 months)"
                next_question = generate_availability_question()  
                user_session["questions"].append(next_question)
                user_session["availability"] = True 
                return jsonify({"question": next_question, "clear_input": True})
                 
            # return final_result(agent="B")
        


        user_input_with_history = ""
        if len(user_session["responses"]) > 0:
            user_input_with_history += f"User: {user_session['query']}\n\n"
            for i, (response, question) in enumerate(zip(user_session["responses"], user_session["questions"])):
                user_input_with_history += f"Assistant{i+1}: {question}\nUser{i+1}: {response}\n\n"
        next_question = agent_b_followup(user_input_with_history)
        user_session["questions"].append(next_question)
        return jsonify({"question": next_question, "clear_input": True})



        # If more questions needed, generate the next one
        # next_question = agent_b_followup(user_session["responses"])
        # user_session["questions"].append(next_question)

        # return jsonify({"question": next_question})

    # Prevent Agent A from interfering if Agent B was assigned
    # if assigned_agent == "A":
    #     logging.info("Agent A is handling the query.")
    #     answer = agent_a_answer(user_response)
    #     user_session.clear()  # Reset after answering
    #     return jsonify({
    #         "final_response": False,
    #         "result": f"✅ Agent A: {answer}"})

    return jsonify({"error": "Unexpected behavior. Please state your query."}), 500


def final_result(agent, answer=None):
    
    user_session["conversation_ended"] = True  # Mark conversation as ended
    if "assigned_agent" in user_session:
        del user_session["assigned_agent"]

    if agent == "A":
        # user_session.clear()  # Reset session after completion
        return jsonify({
            "final_response": False,
            "greeting": False,
            "result": f"✅ Agent A: {answer}"})  # Return Agent A's final result

    elif agent == "B":
        avg_score = sum(s["score"] for s in user_session["scores"]) / len(user_session["scores"])
        user_level = "Beginner" if avg_score < 2 else "Intermediate" if avg_score < 3.5 else "Advanced"

        summary = agent_b_summarize_learning(user_session["responses"], user_session["user_availability"])
        key_elements = agent_b_extract_key_elements(summary,user_level)
        logging.info(f"User level: {user_level}")
    
        relevant_topic_ids = find_relevant_topic_ids(summary)
        relevant_user_level_id = find_relevant_user_level_ids(user_level)
        relevant_doc_ids = filter_records_by_topics_and_user_level(relevant_topic_ids, relevant_user_level_id)

        rag_response = query_rag(summary, relevant_doc_ids)
        score_breakdown = user_session["scores"]
        user_availability = user_session["user_availability"]
        # user_session.clear()  # Clear session after completion
        logging.info(f"RAG Response: {rag_response}")
        return jsonify({
            "user_availability": user_availability,
            "final_response": True,
            "greeting": False,
            "user_level": user_level,
            "summary": summary,
            "key_elements": key_elements,
            "score_breakdown": score_breakdown,
            "relevant_topic_ids": relevant_topic_ids,
            "relevant_user_level_ids": relevant_user_level_id,
            "rag_response": rag_response[0],
            "sources": rag_response[1],
            "sources_links": rag_response[2],
        })

    else:
        return jsonify({"error": "Unexpected behavior. No valid agent assigned."}), 500



if __name__ == "__main__":
    app.run(debug=True)