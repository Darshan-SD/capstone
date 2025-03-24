from flask import Flask, request, jsonify, render_template
from langchain_google_genai import GoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
import os
import json
import logging
from query_data import query_rag
import pandas as pd
from dotenv import load_dotenv
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
load_dotenv()
# Set up Google Gemini LLM
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

MIN_QUESTIONS = 1
MAX_QUESTIONS = 1

# Excel files
main_excel_file = "Resources Version 3.xlsx"
topic_ids_excel_file = "topic_ids_v3.xlsx"
user_level_ids_excel_file = "user_level_ids.xlsx"

# Excel file sheets
main_sheet = "main"

# Excel file columns
main_topic_ids_col = "Topic_ids"
main_user_level_col = "Difficulty Level"
main_chromadb_doc_id_col = "doc_id"

topicids_col = "key_name"
topicids_value_col = "value"

# Global session storage
user_session = {
    "query": None,
    "responses": [],
    "questions": [],
    "question_count": 0,  # number of questions asked so far
    "scores": [],
}


def call_gemini(prompt, max_tokens=100, temperature=0.5):
    """Helper function to call Gemini LLM."""
    logging.info("Calling Gemini with prompt: %s", prompt)
    try:
        response = llm.invoke(prompt)
        logging.info("Gemini response: %s", response)
        return response.strip() if response else ""
    except Exception as e:
        logging.error("Error with Gemini API: %s", e)
        return ""

def is_ai_ml(text):
    """Check if the text mentions AI/ML content."""
    keywords = ["ai", "artificial intelligence", "machine learning", "deep learning", "neural network", "data science", "ml"]
    result = any(kw in text.lower() for kw in keywords)
    logging.info("Checking if text is AI/ML related: %s -> %s", text, result)
    return result

def is_valid_followup_response(response, last_question):
    """Validate if the user's follow-up response is relevant to the follow-up question."""
    # prompt = (
    #     f"Evaluate if the user's response addresses the follow-up question in the AI/ML domain.\n"
    #     f"Follow-up question: \"{last_question}\"\n"
    #     f"User response: \"{response}\"\n\n"
    #     "Final Answer: on-topic or off-topic."
    # )
    # classification = call_mistral(prompt, max_tokens=50, temperature=0.3)
    # logging.info("Follow-up validation result: %s", classification)
    # return "on-topic" in classification.lower() if classification else False
    return "on-topic"


# NEW
# def generate_question():
#     """
#     Generate a follow-up question dynamically based on full conversation history,
#     ensuring logical progression without hallucinations.
#     """
#     if not user_session["responses"]:  # If no responses yet, provide a starting question
#         return "What aspect of AI/ML interests you the most?"

#     conversation_context = "\n".join([
#         f"Q: {q}\nA: {a}" for q, a in zip(user_session["questions"], user_session["responses"])
#     ])

#     examples = sample_data["EXAMPLES"]

#     # Format examples for Gemini (showing different levels)
#     examples_text = ""
#     for level, interactions in examples.items():
#         examples_text += f"\n### {level} User Examples ###\n"
#         for ex in interactions[:5]:  # Show 5 examples per level
#             examples_text += (
#                 f"User was asked: \"{ex['follow_up_question']}\"\n"
#                 f"User responded: \"{ex['user_response']}\"\n"
#                 f"Expected follow-up: \"{ex['expected_follow_up']}\"\n\n"
#             )

#     # Instruction for Gemini
#     prompt = (
#         f"I am developing an AI chatbot that adapts to users at different AI/ML experience levels.\n"
#         f"Users may be beginners, intermediates, or advanced practitioners.\n\n"
#         f"Below is the conversation so far:\n\n"
#         f"{conversation_context}\n\n"
#         f"Here are some sample interactions from different levels:\n"
#         f"{examples_text}\n"
#         f"The latest user response is: \"{user_session['responses'][-1]}\"\n\n"
#         f"Now, generate the next follow-up question that logically continues this conversation.\n"
#         f"STRICT RULES:\n"
#         f"- DO NOT change the topic or reset the discussion.\n"
#         f"- If the user is vague or uncertain (e.g., 'I don't know' or 'I'm not sure'), clarify while staying within the SAME topic.\n"
#         f"- Ensure the question is engaging, relevant, and builds upon the user's last clear statement.\n"
#     )
#     print(prompt)
#     # Generate the next follow-up question using Gemini
#     generated_question = call_gemini(prompt, max_tokens=50, temperature=0.7)

#     # 🔹 If Gemini fails to generate a response, ask for clarification based on the last user response
#     if not generated_question:
#         return f"I didn't fully understand your last response: \"{user_session['responses'][-1]}\". Could you clarify what you meant?"

#     return generated_question

def generate_question(context):
    """Generate a concise follow-up question in the AI/ML domain."""
    logging.info("Generating follow-up question for context: %s", context)
    # prompt = (
    #     f"You are expert in generating very concise questions to understand the users current level of knowledge in the field of Artificial Intelligence and Machine Learning. Refer following conversation to understand better.\n"

    #     "I want to learn ai\n"

    #     "Do you have any prior experience in Artificial Intelligence or Machine Learning?\n"
    #     "No and also I have no experience in programming\n"

    #     "Do you know any math concepts such as Linear Algebra and Calculus?\n"
    #     "yeah but I do not remember them as of now\n"

    #     f"Now only generate one question for the following conversation/query. Make sure you do not repeat questions based on user's answers:\n{context}"
    # )

    prompt = (
    f"You are an expert in generating concise, targeted questions to assess a user's current knowledge in Artificial Intelligence and Machine Learning (AI/ML). "
    "Your role is to engage in natural, conversational interactions while:\n"
    "- Evaluating user needs and knowledge level.\n"
    "- Understand how long user is willing to spend learning.\n"
    "- Recommending appropriate learning resources.\n"
    "- Explaining concepts clearly.\n"
    "- Encouraging and motivating the user.\n\n"
    
    "### STRICT RULES:\n"
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

    question = call_gemini(prompt, max_tokens=50, temperature=0.5) or {
        "question": "Could you share more about your experience with AI/ML?"
    }
    if "```" in question:
        question = question.split("```json")[1].split("```")[0].strip()
        
    question = json.loads(question)["question"]
    logging.info("Generated question: %s", question)
    return question


# NEW
# def generate_summary(responses):
#     """Generate a summary of what the user wants to learn based on their responses."""
#     prompt = (
#         f"Summarize the user's learning goals based on these responses:\n"
#         f"{responses}\n"
#         "Provide a concise summary.")
#     return call_gemini(prompt, max_tokens=100, temperature=0.5)

def generate_summary(initial_query, responses, questions):
    """Generate a summary sentence combining the initial query with all responses."""
    logging.info("Generating summary for query: %s with responses: %s", initial_query, responses)
    conversation = f"Initial Query: {initial_query}\n"
    for i, (response, question) in enumerate(zip(responses, questions)):
        conversation += f"Question{i+1}: {question}\nUser Response{i+1}: {response}\n"
    # responses_text = " ".join(responses)
    prompt = (
        f"Summarize the user's AI/ML needs based on the following information:\n"
        f"{conversation}\n"
        "Provide a concise sentence summarizing what the user specifically wants in the AI/ML domain."
    )
    logging.info("Generating summary with prompt: %s", prompt)
    summary = call_gemini(prompt, max_tokens=100, temperature=0.5) or "Summary generation failed."
    logging.info("Generated summary: %s", summary)
    return summary

def score_response_with_context(response, question):
    """
    Use OpenAI to score a single response in the context of its follow-up question on a scale of 0 to 5.
    """
    prompt = (
        f"Evaluate the following user response in the context of its follow-up question in the AI/ML domain.\n\n"
        f"Follow-up question: \"{question}\"\n"
        f"User response: \"{response}\"\n\n"
        "On a scale from 0 to 5, score the response. Provide a brief explanation, then output 'Final Score: X' on a new line."
    )
    result = call_gemini(prompt, max_tokens=100, temperature=0.5)
    score = 0
    try:
        for line in result.splitlines():
            if "final score:" in line.lower():
                score_str = line.lower().split("final score:")[1].strip().split()[0]
                score = int(score_str)
                break
    except Exception as e:
        print(f"Error extracting score: {e}")
    return score, result





# NEW
def score_response(response, question):
    """
    Evaluate user response and infer expertise level along with whether more questions are needed.
    """
    prompt = (
        f"Evaluate this user response in relation to the follow-up question in AI/ML.\n\n"
        f"Follow-up question: \"{question}\"\n"
        f"User response: \"{response}\"\n\n"
        "On a scale from 0 to 5, where 0 means no relevant information and 5 means an exceptional response, "
        "score the response. Also, analyze if the response aligns more with a Beginner, Intermediate, or Advanced user."
        "Finally, decide if the chatbot should ask more follow-up questions (Yes/No).\n"
        "Provide output as:\n"
        "Final Score: X\n"
        "Reasoning: Explain why the response received this score.\n"
        "User Level: [Beginner/Intermediate/Advanced]\n"
        "More Questions Needed: [Yes/No]")

    result = call_gemini(prompt, max_tokens=150, temperature=0.3)

    score = 0
    reasoning = "No explanation provided."
    user_level = "Unknown"
    more_questions_needed = "Yes"

    try:
        for line in result.splitlines():
            if "Final Score:" in line:
                try:
                    score = int(line.split(":")[1].strip())
                except ValueError:
                    score = 0  # Default to 0 if conversion fails
            if "Reasoning:" in line:
                reasoning = line.split(":", 1)[1].strip()
            if "User Level:" in line:
                user_level = line.split(":")[1].strip()
            if "More Questions Needed:" in line:
                more_questions_needed = line.split(":")[1].strip()
    except Exception as e:
        print(f"Error extracting score: {e}")

    return score, reasoning, user_level, more_questions_needed

# def score_responses(responses, questions):
#     """Score all follow-up responses."""
#     total_score = 0
#     breakdown = []
#     for i, response in enumerate(responses):
#         question = questions[i] if i < len(questions) else "No corresponding question."
#         score, explanation = score_response_with_context(response, question)
#         total_score += score
#         breakdown.append(f"Q{i+1}: Score {score}. Explanation: {explanation}")
#     average_score = total_score / len(responses) if responses else 0
#     return average_score, breakdown


# def determine_user_level(average_score):
#     """Determine user level based on average score."""
#     logging.info("Determining user level for average score: %s", average_score)
#     if average_score < 2.0:
#         return "Beginner in the AI/ML domain."
#     elif average_score < 3.5:
#         return "Intermediate in the AI/ML domain."
#     return "Advanced AI/ML practitioner with strong theoretical and practical experience."

# Function to read topic IDs from an Excel file
def get_topic_ids(file_path=topic_ids_excel_file):
    """Reads topic IDs from an Excel file and returns a dictionary of topics and their IDs."""
    # try:
    df = pd.read_excel(file_path, sheet_name="topic_ids")
    topic_dict = dict(zip(df[topicids_col], df[topicids_value_col]))  # Assuming columns are 'Topic' and 'ID'
    logging.info("Loaded topic IDs successfully.")
    return topic_dict
    # except Exception as e:
    #     logging.error("Error reading topic IDs: %s", e)
    #     return {}

# Function to find relevant topic IDs based on the summary
def find_relevant_topic_ids(summary, topic_dict):
    """Find relevant topic IDs for a given summary using Gemini."""
    topics_str = "\n".join([f"{topic}: {topic_id}" for topic, topic_id in topic_dict.items()])
    print(f"\n\n\nTopics: {topics_str}\n\n\n")
    prompt = (
        f"Given the following AI/ML-related summary:\n"
        f"{summary}\n\n"
        f"Here are topics and their IDs:\n{topics_str}\n\n"
        f"Identify the most relevant topic IDs based on the summary. Output the IDs separated by commas. For example, you identified four relevant IDs. The output structure should be 'number1,number2,number3,number4'"
    )
    response = call_gemini(prompt) # Output: 19, 2, 20
    relevant_ids = list(map(int, response.split(","))) if response else []
    
    # Extract relevant IDs from the response
    # relevant_ids = [topic_dict[topic] for topic in topic_dict if topic.lower() in response.lower()]
    logging.info("Relevant topic IDs: %s", relevant_ids)
    return relevant_ids

# Function to read user level IDs from an Excel file
def get_user_level_ids(file_path=user_level_ids_excel_file):
    """Reads topic IDs from an Excel file and returns a dictionary of topics and their IDs."""
    try:
        df = pd.read_excel(file_path, sheet_name="user_level_ids")
        user_level_dict = dict(zip(df["User Level"], df["ID"])) 
        logging.info("Loaded user_level IDs successfully.")
        return user_level_dict
    except Exception as e:
        logging.error("Error reading topic IDs: %s", e)
        return {}
    
# Function to find relevant user level IDs based on the summary
def find_relevant_user_level_ids(summary, user_level_dict):
    """Find relevant topic IDs for a given summary using Gemini."""
    user_level_str = "\n".join([f"{user_level}: {user_level_id}" for user_level, user_level_id in user_level_dict.items()])
    print(f"\n\n\nUser Levels: {user_level_str}\n\n\n")
    prompt = (
        f"Given the following AI/ML-related summary:\n"
        f"{summary}\n\n"
        f"Here are user levels and their IDs:\n{user_level_str}\n\n"
        f"Identify the most relevant user level ID based on the summary. Output only one ID. For example, '2'."
    )
    response = call_gemini(prompt) # Output: 19, 2, 20
    relevant_id = int(response) if response else []
    
    # Extract relevant IDs from the response
    # relevant_ids = [topic_dict[topic] for topic in topic_dict if topic.lower() in response.lower()]
    logging.info("Relevant User Level ID: %s", relevant_id)
    return relevant_id

def filter_records_by_topics_and_user_level(file_path, sheet_name, input_list, user_level_id):
    # Read Excel file
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Ensure 'Topics' column is treated as a list
    df[main_topic_ids_col] = df[main_topic_ids_col].apply(lambda x: [int(i) for i in str(x).split(',')])

    # Ensure 'User Level' column is treated correctly (assuming it's a string of IDs like "1,2,3")
    df[main_user_level_col] = df[main_user_level_col].apply(lambda x: [int(i) for i in str(x).split(',')])

    print(f"\n\nAll DOC IDs: {df[main_chromadb_doc_id_col].values.tolist()}\n\n")

    # Function to check if user level matches
    def user_level_matches(record):
        return user_level_id in record

    # Function to check if any topic ID matches
    def topics_matches(record):
        return any(num in record for num in input_list)

    # Apply filtering on both user level and topics
    filtered_df = df[df[main_topic_ids_col].apply(topics_matches) & df[main_user_level_col].apply(user_level_matches)]

    print(f"\n\nFiltered DF: {filtered_df[main_chromadb_doc_id_col].values.tolist()}\n\n")

    return filtered_df[main_chromadb_doc_id_col].values.tolist()




# NEW
def extract_key_elements(summary, user_level):
    """Extract key elements from the summary and include the user's level."""
    prompt = (f"Extract the key topics from the following summary:\n"
              f"{summary}\n"
              f"Ensure to include the user's level: {user_level}.\n"
              "Provide only the key elements as a comma-separated list.")
    key_elements = call_gemini(prompt, max_tokens=50, temperature=0.3)

    elements = key_elements.split(", ")
    if user_level.lower() not in [e.lower() for e in elements]:
        elements.append(user_level)  # Ensure the user level is included

    return elements

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.json
    user_input = data.get("input")
    logging.info("Received user input: %s", user_input)
    if not user_input:
        return jsonify({"error": "Please enter your query or response."}), 400

    # Initial query handling
    if user_session["query"] is None:
        # if not is_ai_ml(user_input):
        #     return jsonify({"message": "Please enter a query related to AI/ML."}), 400
        user_session.update({"query": user_input, "responses": [], "questions": [], "question_count": 1, "scores": []})
        first_question = generate_question(user_input)
        user_session["questions"].append(first_question)
        return jsonify({"final_response": False, "question": first_question, "clear_input": True})

    last_question = user_session["questions"][-1]
    user_session["responses"].append(user_input)

    score, reasoning, inferred_level, more_questions_needed = score_response(user_input, last_question)
    user_session["scores"].append({"response": user_input, "score": score, "reasoning": reasoning})

    # Check if the session has enough responses for scoring
    if user_session["question_count"] >= MAX_QUESTIONS or len(user_session["responses"]) >= MIN_QUESTIONS:
        summary = generate_summary(user_session["query"], user_session["responses"], user_session["questions"])
        key_elements = extract_key_elements(summary, inferred_level)

        user_level_dict = get_user_level_ids()
        print(f"\n\n\nUser Level Dict: {user_level_dict}\n\n\n")
        relevant_user_level_id = find_relevant_user_level_ids(summary, user_level_dict)

        topic_dict = get_topic_ids()
        relevant_topic_ids = find_relevant_topic_ids(summary, topic_dict)
        relevant_doc_ids = filter_records_by_topics_and_user_level(main_excel_file, main_sheet, relevant_topic_ids, relevant_user_level_id)
        print(relevant_doc_ids)
        rag_response = query_rag(summary, relevant_doc_ids)
        logging.info("Finalizing session. Score: %s, Summary: %s, Relevant IDs: %s", user_session["scores"], summary, relevant_topic_ids)

        return jsonify({
            "final_response": True,
            "result": f"User Level: {inferred_level}",
            "score_breakdown": user_session["scores"],
            "summary": summary,
            "key_elements": key_elements,

            "relevant_topic_ids": relevant_topic_ids,
            "relevant_user_level_ids": relevant_user_level_id,
            "rag_response": rag_response[0],
            "sources": rag_response[1],
            "sources_links": rag_response[2],
            # "filtered_docs": rag_response[3],
            "responses": user_session["responses"]
        })

    user_input_with_history = ""
    if len(user_session["responses"]) > 0:
        user_input_with_history += f"User: {user_session['query']}\n\n"
        for i, (response, question) in enumerate(zip(user_session["responses"], user_session["questions"])):
            user_input_with_history += f"Assistant{i+1}: {question}\nUser{i+1}: {response}\n\n"
    next_question = generate_question(user_input_with_history)
    user_session["questions"].append(next_question)
    return jsonify({"final_response": False, "question": next_question, "clear_input": True})

if __name__ == "__main__":  
    app.run(debug=True)
