from flask import Flask, request, jsonify, render_template
from langchain_community.llms import Ollama
import os
import json
import logging
import pandas as pd
from query_data import query_rag
from dotenv import load_dotenv
import re  # Import regex for extracting numbers

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
    Master Agent: Determines if the query goes to Agent A (FAQ) or Agent B (Learning Plan).
    Returns: "A" or "B"
    """
    master_prompt = (
    "You are an AI assistant classifying user queries into two categories:\n"

    "- 'A' → The user is asking a factual AI/ML question or casual Hi/Hello/How are you? chat (e.g., 'What is deep learning?', 'hey', 'hello').\n"
    "- 'B' → The user wants to learn in AI/ML field and requesting a learning plan (e.g., 'I want to learn transformers.', 'I want to learn about computer vision.').\n"

    "**RULES:**\n"
    "- ONLY return 'A' or 'B'. DO NOT return any extra text.\n"
    "- If the query is a general AI learning request (e.g., 'I want to learn AI'), classify as 'B'.\n"
    "- If the query asks about a specific AI/ML concept to explain (e.g., 'Explain backpropagation'), classify as 'A'.\n"
    f"- Give JSON Response Only. For example:\n"
    "{\n"
    '  "category": "A"\n'
    "}\n\n"
    
    f"User Query: {user_query}"
    )

    # Invoke LLM with lower temperature
    response = llm_master.invoke(master_prompt).strip()
    logging.info(f"Master Agent raw response: '{response}'")
    response = json.loads(response)["category"]

    # Add debug logging to track the raw response
    logging.info(f"Master Agent raw response: '{response}'")

    # Extract classification result
    classification = response if response in ["A", "B"] else "Unknown"

    # Retry classification if "Unknown"
    if classification == "Unknown":
        logging.warning(f"Master Agent struggled to classify: '{user_query}'. Retrying with a refined prompt...")
        
        retry_prompt = f"""
        Classify the user query into "A" or "B" based on these rules:

        - "A" → Factual AI/ML question (e.g., "What is deep learning?")
        - "B" → Learning request (e.g., "I want to learn transformers.")

        **STRICT RULE:** Return ONLY "A" or "B". No extra text.

        User Query: "{user_query}"
        
        **Final Answer:** (Only "A" or "B")
        """
        response = llm_master.invoke(retry_prompt).strip()
        logging.info(f"Master Agent retry response: '{response}'")
        classification = response if response in ["A", "B"] else "Unknown"

    logging.info(f"Master Agent classified the query as: {classification}")
    return classification

### 2️ Agent A: Provide Direct Answer ###
def agent_a_answer(user_query):
    """
    Agent A (FAQ Handler): Provides direct AI/ML answers without RAG.
    """
    prompt = f"Provide a concise, factual answer to this user query and stick to  AI/ML field only: {user_query}"
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

    Identify the most relevant topic IDs. Output only the IDs separated by commas.
    """
    response = llm_agent_b.invoke(prompt).strip()
    return list(map(int, response.split(","))) if response else []

### 7️ Read User Level IDs from Excel ###
def get_user_level_ids():
    df = pd.read_excel(user_level_ids_excel_file, sheet_name="user_level_ids")
    return dict(zip(df["User Level"], df["ID"]))

### 8 Find User Level ID ###
def find_relevant_user_level_ids(summary):
    user_level_dict = get_user_level_ids()
    levels_str = "\n".join([f"{level}: {level_id}" for level, level_id in user_level_dict.items()])
    
    prompt = f"""
    Given the AI/ML-related summary:
    "{summary}"
    Here are user levels and their IDs:
    {levels_str}

    Identify the most relevant user level ID.
    
    **STRICT RULE:**
    - Return ONLY the ID as a single number.
    - DO NOT include any extra text.

    Example Output: `2`
    """

    response = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Raw User Level Response: {response}")

    # Extract only the first number from the response
    match = re.search(r"\d+", response)
    if match:
        return int(match.group(0))  # Convert extracted number to int

    logging.error("Could not extract a valid user level ID.")
    return None  # Return None if no valid ID found

### 9 Filter Relevant Resources ###
def filter_records_by_topics_and_user_level(relevant_topic_ids, user_level_id):
    df = pd.read_excel(main_excel_file, sheet_name=main_sheet)
    df[main_topic_ids_col] = df[main_topic_ids_col].apply(lambda x: [int(i) for i in str(x).split(',')])
    df[main_user_level_col] = df[main_user_level_col].apply(lambda x: [int(i) for i in str(x).split(',')])

    filtered_df = df[
        df[main_topic_ids_col].apply(lambda record: any(num in record for num in relevant_topic_ids)) &
        df[main_user_level_col].apply(lambda record: user_level_id in record)
    ]
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
def agent_b_summarize_learning(responses):
    """
    Summarizes what the user wants to learn based on all responses.
    """
    prompt = f"""
    Given the following user responses related to AI/ML learning, generate a summary of their learning goals:

    {responses}

    The summary should be concise and highlight what the user wants to learn.

    Return as a single summary sentence.
    """

    summary = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Generated User Learning Summary: {summary}")
    return summary

### extracting key elements ###
def agent_b_extract_key_elements(summary):
    """
    Extracts key AI/ML topics from the user’s learning summary.
    """
    prompt = f"""
    Given the following summary of the user's AI/ML learning goals:
    
    "{summary}"
    
    Extract key concepts or topics that are relevant. These should be specific to AI/ML learning (e.g., "Neural Networks", "Computer Vision", "Supervised Learning").
    
    Return a comma-separated list of key topics.
    """

    key_elements_response = llm_agent_b.invoke(prompt).strip()
    key_elements = key_elements_response.split(", ")  # Convert response into a list

    logging.info(f"Extracted Key Elements: {key_elements}")
    return key_elements

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
        if question_index >= len(user_session["questions"]):
            return jsonify({"error": "Invalid question index."}), 400

        question = user_session["questions"][question_index]
        logging.info(f"Received user response: {user_response}")
        score, reasoning, more_questions_needed = agent_b_score_response(user_response, question)

        user_session["responses"].append(user_response)
        user_session["scores"].append({"response": user_response, "score": score, "reasoning": reasoning})

        logging.info(f"Uset Session: {user_session}")

        # If max questions reached or no more questions needed → Final Response
        if len(user_session["responses"]) >= MAX_QUESTIONS or more_questions_needed == "No":
           return final_result(agent="B")
        


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
            "result": f"✅ Agent A: {answer}"})  # Return Agent A's final result

    elif agent == "B":
        avg_score = sum(s["score"] for s in user_session["scores"]) / len(user_session["scores"])
        user_level = "Beginner" if avg_score < 2 else "Intermediate" if avg_score < 3.5 else "Advanced"

        summary = agent_b_summarize_learning(user_session["responses"])
        key_elements = agent_b_extract_key_elements(summary)

        relevant_topic_ids = find_relevant_topic_ids(summary)
        relevant_user_level_id = find_relevant_user_level_ids(summary)
        relevant_doc_ids = filter_records_by_topics_and_user_level(relevant_topic_ids, relevant_user_level_id)

        rag_response = query_rag(summary, relevant_doc_ids)
        score_breakdown = user_session["scores"]

        # user_session.clear()  # Clear session after completion

        return jsonify({
            "final_response": True,
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