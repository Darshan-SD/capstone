from config import llm_master, llm_agent_a, llm_agent_b, RETRY_ERROR
from controllers.utils import get_topic_ids
from controllers.prompts import ( master_prompt_function, 
                                 agent_a_answer_prompt, 
                                 agent_b_followup_prompt, 
                                 agent_b_score_response_prompt, 
                                 agent_b_summarize_learning_prompt, 
                                 agent_b_extract_key_elements_prompt, 
                                 response_greeting_prompt, 
                                 generate_availability_question_prompt,
                                 check_is_regenerate_query_prompt,
                                 regenerate_query_prompt,
                                 modify_summary_prompt )
import json
import logging
import random
from flask import session, jsonify
import ast
from dotenv import load_dotenv
import os
from langchain_google_genai import GoogleGenerativeAI

load_dotenv()

# TEST SCRIPT
# random_bool = random.choice([True, False])
# print("Random bool: ", random_bool)
# if random_bool == True:
#     response = '{ "category": "A }'
# else:
#     response = llm_master.invoke(master_prompt).strip()
#     logging.info(f"Raw response: '{response}'")
#     response_data = json.loads(response)

### Master Agent: Classify Query ###
def classify_query(user_query):
    """
    Master Agent: Determines if the query goes to Agent A (FAQ), Agent B (Learning Plan), 
    or if the user is greeting (redirecting them to AI/ML questions).
    Returns: "A", "B", or "GREET"
    """
    try:
        master_prompt = master_prompt_function(user_query)
        response = llm_master.invoke(master_prompt).strip()
        logging.info(f"Master Agent raw response: '{response}'")
        response_data = json.loads(response)
        classification = response_data.get("category", "Unknown")
    except Exception as e:
        logging.error(f"Master Agent failed to classify the query. Error: {e}")
        classification = "Unknown"

    # If the query is a greeting, provide a polite redirection message
    if classification == "GREET":
        logging.info("Master Agent detected a greeting. Redirecting user to AI/ML domain.")
    elif classification == "Unknown":
        logging.warning(f"Master Agent struggled to classify: '{user_query}'. Sending retry prompt to frontend.")

    logging.info(f"Master Agent classified the query as: {classification}")
    return classification

### Agent A: Provide Direct Answer ###
def agent_a_answer(user_query):
    """
    Agent A (FAQ Handler): Provides direct AI/ML answers without RAG.
    """
    try:
        prompt = agent_a_answer_prompt(user_query)
        logging.info(f"Agent A prompt: {prompt}")
        response = llm_agent_a.invoke(prompt).strip()
        response = json.loads(response)
    except Exception as e:
        logging.error(f"Agent A failed to provide a response. Error: {e}")
        return {"agent_a_error": RETRY_ERROR}

    logging.info(f"Agent A provided response: {response}")
    return response

### Agent B: Generate Follow-up Questions ###
def agent_b_followup(context):
    """
    Agent B generates one follow-up question at a time based on previous responses.
    It dynamically decides whether more questions are needed.
    """
    try:
        prompt = agent_b_followup_prompt(context)
        logging.info(f"\n\n\nAgent B follow-up prompt: {prompt}\n\n\n")
        response = llm_agent_b.invoke(prompt).strip()
        if "```" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        response = json.loads(response)
    except Exception as e:
        logging.error(f"Agent B failed to provide a response. Error: {e}")
        return {"agent_b_error": RETRY_ERROR}

    logging.info(f"Agent B generated follow-up: {response}\n\n\n")   
    logging.info("Generated question: %s", response)
    return response





### Agent B: Score User Responses ###
def agent_b_score_response(response, question, question_count):
    """
    Scores a user's response based on depth, correctness, and relevance.
    Also determines whether another question is needed (within limits).
    """
    prompt = agent_b_score_response_prompt(response, question, question_count)
    logging.info(f"\n\n\nScoring User Prompt: {prompt}\n\n\n")
    logging.info(f"\n\n\nUser Response with Question: {response, question}\n\n\n")
    result = llm_agent_b.invoke(prompt).strip()
    result_data = json.loads(result)

    logging.info(f"Scored Response: {result_data}")
    return result_data["score"], result_data["reasoning"], result_data["more_questions_needed"]

### Summarizing user response ###
def agent_b_summarize_learning(responses, user_availability):
    """
    Summarizes what the user wants to learn based on all responses, including availability.
    """
    prompt = agent_b_summarize_learning_prompt(responses, user_availability)
    summary = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Generated User Learning Summary: {summary}")
    return summary

### extracting key elements ###
def agent_b_extract_key_elements(summary,user_level):
    """
    Extracts key AI/ML topics from the user’s learning summary and includes the user level.
    """
    prompt = agent_b_extract_key_elements_prompt(user_level, summary)
    key_elements_response = llm_agent_b.invoke(prompt).strip()
    key_elements = key_elements_response.split(", ")  # Convert response into a list
    logging.info(f"Extracted Key Elements: {key_elements}")
    return key_elements

def respond_greeting(user_query):
    logging.info("Master Agent detected a greeting. Generating a dynamic greeting response.")

    topic_dict = get_topic_ids()
    topics_str = "\n".join([f"{topic}" for topic, topic_id in topic_dict.items()])

    greeting_prompt = response_greeting_prompt(topics_str, user_query)

    greeting_response = llm_master.invoke(greeting_prompt).strip()
    greeting_response = json.loads(greeting_response)
    logging.info(f"Greeting response generated: '{greeting_response}'")

    return greeting_response

def generate_availability_question():
    """
    Uses the LLM to dynamically generate a question about the user's availability.
    """
    prompt = generate_availability_question_prompt()

    response = llm_agent_b.invoke(prompt).strip()
    response = json.loads(response)
    logging.info(f"Generated Availability Question: {response}")
    return response

def is_regeneration_request(user_input):
    
    """
    Uses the LLM to dynamically determine if the user is asking to regenerate the given course.
    """
    prompt = check_is_regenerate_query_prompt(user_input)

    response = llm_agent_b.invoke(prompt).strip()
    logging.info(f"Is course plan regeneration neeeded? : {response}")
    return response.lower()

def regenerate_learning_plan(user_input):
    """
    Uses the LLM to regenerate the given course.
    """
    try:
        # Pull from Redis session
        existing_plan = session.get("ragResponse")
        filtered_docs = session.get("filteredDocs")
        key_elements = session.get("keyElements")
        if not existing_plan:
            logging.warning("No existing course plan found in session.")
            return jsonify({"error": "No existing course to modify."}), 400
        if not filtered_docs:
            logging.warning("No existing filterd docs found in session.")
            return jsonify({"error": "No existing filterd docs found!."}), 400
        if not key_elements:
            logging.warning("No key elements found in session.")
            return jsonify({"error": "No existing key elements found!."}), 400

        prompt = regenerate_query_prompt(existing_plan, user_input, filtered_docs, key_elements)

        # Call LLM
        GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
        llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)

        response_text = llm.invoke(prompt).strip()
        #response_text = llm_agent_b.invoke(prompt).strip()

        # Clean up if it's inside markdown formatting
        if "```" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()

        # ✅ NEW: Safely convert Python-style dict to JSON
        try:
            logging.info(f"🧾 Raw LLM response before parsing:\n{response_text}")

            python_dict = ast.literal_eval(response_text)  # Convert to Python dict
            response_text = json.dumps(python_dict)        # Convert to valid JSON string
            response_text = json.loads(response_text)      # Parse as JSON

        except Exception as parse_error:
            logging.error(f"❌ JSON decoding failed: {parse_error}")
            logging.error(f"LLM Raw Response:\n{response_text}")
            return jsonify({"retry_error": "The learning plan couldn't be regenerated due to a formatting issue."}), 500

        # Print formatted response
        formatted_response = f"""
        \n\n---------------Revised RESPONSE-----------------
        Response: {response_text}
        ----------------------------------------
        """
        print(formatted_response)

        #modify the exisiting user summary
        updated_summary = update_user_goal_summary(session.get("summary", ""),  user_input)
        
        modified_summary_print = f"""
        \n\n---------------Modified Summary-----------------
        Summary: {updated_summary}
        ----------------------------------------
        """
        print(modified_summary_print)

        # Update the session with the new plan
        session["ragResponse"] = response_text
        session["summary"] = updated_summary
        session["regeneration_mode"] = False
        session["conversation_ended"] = True
        logging.info("✅ Course plan successfully regenerated.")
        
        # Reuse original source links & metadata
        score_breakdown = session["scores"]
        user_availability = session["user_availability"]
        
        #update user summary before sending the final response

        return jsonify({
            "user_availability": user_availability,
            "final_response": True,
            "greeting": False,
            "user_level": session.get("usrLevel", ""),
            "summary": session.get("summary", ""),
            "key_elements": session.get("keyElements", ""),
            "score_breakdown": session.get("scores", ""),
            "relevant_topic_ids": [],
            "relevant_user_level_ids": [],
            "rag_response": response_text,
            "sources": session.get("sources", []),
            "sources_links": session.get("sources_links", []),
        })

    except Exception as e:
        logging.error(f"Error regenerating learning plan: {e}")
        return jsonify({"retry_error": RETRY_ERROR}), 500


def update_user_goal_summary(existing_summary, user_input):

    prompt = modify_summary_prompt(existing_summary, user_input)

    return llm_agent_b.invoke(prompt).strip()

