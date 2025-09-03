from config import llm_master, llm_agent_a, llm_agent_b, RETRY_ERROR, OPEN_ROUTER_HEADERS, OPEN_ROUTER_API_URL, open_router_data
from controllers.utils import get_topic_ids
from controllers.prompts import ( master_prompt_function, 
                                 agent_a_answer_prompt, 
                                 agent_b_followup_prompt, 
                                 agent_b_score_response_prompt, 
                                 agent_b_summarize_learning_prompt, 
                                 agent_b_extract_key_elements_prompt, 
                                 response_greeting_prompt, 
                                 generate_availability_question_prompt )
import json
import logging
import random
import requests

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
        # ---------------- LOCAL LLM --------------------
        # response = llm_master.invoke(master_prompt).strip()
        # logging.info(f"Master Agent raw response: '{response}'")
        # response_data = json.loads(response)
        # classification = response_data.get("category", "Unknown")
        # ---------------- LOCAL LLM --------------------

        # ---------------- OPENROUTER LLM -----------------
        response = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("master", master_prompt))
        if response.status_code == 200:
            response_data = response.json()["choices"][0]["message"]["content"]
            response_data = json.loads(response_data)
            logging.info(f"(OPEN ROUTER) Master Agent raw response: '{response_data}'")
            classification = response_data.get("category", "Unknown")
        else:
            logging.error(f"(OPEN ROUTER) Master Agent API call failed: {response.status_code} - {response.text}")
            classification = "Unknown"
        # ---------------- OPENROUTER LLM -----------------

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

        # ---------------- LOCAL LLM --------------------
        # response = llm_agent_a.invoke(prompt).strip()
        # response = json.loads(response)
        # ---------------- LOCAL LLM --------------------

        # ---------------- OPENROUTER LLM -----------------
        response = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("a", prompt))
        if response.status_code == 200:
            response = response.json()["choices"][0]["message"]["content"]
            response = json.loads(response)
            logging.info(f"(OPEN ROUTER) Agent A raw response: '{response}'")
        else:
            logging.error(f"(OPEN ROUTER) Agent A failed to provide a response: {response.status_code} - {response.text}")
            return {"agent_a_error": RETRY_ERROR}
        # ---------------- OPENROUTER LLM -----------------
        
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

        # ---------------- LOCAL LLM --------------------
        # response = llm_agent_b.invoke(prompt).strip()
        # if "```" in response:
        #     response = response.split("```json")[1].split("```")[0].strip()
        # response = json.loads(response)
        # ---------------- LOCAL LLM --------------------

        # ---------------- OPENROUTER LLM -----------------
        response = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("b", prompt))
        if response.status_code == 200:
            response = response.json()["choices"][0]["message"]["content"]
            response = json.loads(response)
            logging.info(f"(OPEN ROUTER) Agent B Followup raw response: '{response}'")
        else:
            logging.error(f"(OPEN ROUTER) Agent B Followup failed to provide a response: {response.status_code} - {response.text}")
            return {"agent_b_error": RETRY_ERROR}
        # ---------------- OPENROUTER LLM -----------------

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

    # ---------------- LOCAL LLM --------------------
    # result = llm_agent_b.invoke(prompt).strip()
    # result_data = json.loads(result)
    # ---------------- LOCAL LLM --------------------

    # ---------------- OPENROUTER LLM -----------------
    result = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("b", prompt))
    if result.status_code == 200:
        result = result.json()["choices"][0]["message"]["content"]
        result_data = json.loads(result)
        logging.info(f"(OPEN ROUTER) Agent B Score response: '{result_data}'")
    else:
        logging.error(f"(OPEN ROUTER) Agent B Score failed to provide a response: {result.status_code} - {result.text}")
        return {"agent_b_error": RETRY_ERROR}
     # ---------------- OPENROUTER LLM -----------------

    logging.info(f"Scored Response: {result_data}")
    return result_data["score"], result_data["reasoning"], result_data["more_questions_needed"]

### Summarizing user response ###
def agent_b_summarize_learning(responses, user_availability, query):
    """
    Summarizes what the user wants to learn based on all responses, including availability.
    """
    prompt = agent_b_summarize_learning_prompt(responses, user_availability, query)

    # ---------------- LOCAL LLM --------------------
    # summary = llm_agent_b.invoke(prompt).strip()
    # ----------------- LOCAL LLM --------------------

    # ---------------- OPENROUTER LLM -----------------
    result = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("b", prompt))
    if result.status_code == 200:
        result = result.json()["choices"][0]["message"]["content"]
        summary = json.loads(result)
        logging.info(f"(OPEN ROUTER) Agent B Summerize raw response: '{summary}'")
    else:
        logging.error(f"(OPEN ROUTER) Agent B Summerize failed to provide a response: {result.status_code} - {result.text}")
        return {"agent_b_error": RETRY_ERROR}
     # ---------------- OPENROUTER LLM -----------------

    logging.info(f"Generated User Learning Summary: {summary}")
    return summary

### extracting key elements ###
def agent_b_extract_key_elements(summary,user_level):
    """
    Extracts key AI/ML topics from the user’s learning summary and includes the user level.
    """
    prompt = agent_b_extract_key_elements_prompt(user_level, summary)

    # ---------------- LOCAL LLM --------------------
    # key_elements_response = llm_agent_b.invoke(prompt).strip()
    # key_elements = key_elements_response.split(", ")  # Convert response into a list
    # logging.info(f"Extracted Key Elements: {key_elements}")
    # ---------------- LOCAL LLM --------------------

    # ---------------- OPENROUTER LLM -----------------
    result = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("b", prompt))
    if result.status_code == 200:
        key_elements_response = result.json()["choices"][0]["message"]["content"]
        key_elements = key_elements_response.split(", ")  # Convert response into a list
        # key_elements = json.loads(result)
        logging.info(f"(OPEN ROUTER) Agent B Extract Key Elements raw response: '{key_elements}'")
    else:
        logging.error(f"(OPEN ROUTER) Agent B Extract Key Elements failed to provide a response: {result.status_code} - {result.text}")
        return {"agent_b_error": RETRY_ERROR}
     # ---------------- OPENROUTER LLM -----------------

    return key_elements

def respond_greeting(user_query):
    logging.info("Master Agent detected a greeting. Generating a dynamic greeting response.")

    topic_dict = get_topic_ids()
    topics_str = "\n".join([f"{topic}" for topic, topic_id in topic_dict.items()])

    greeting_prompt = response_greeting_prompt(topics_str, user_query)

    # ---------------- LOCAL LLM --------------------
    # greeting_response = llm_master.invoke(greeting_prompt).strip()
    # greeting_response = json.loads(greeting_response)
    # logging.info(f"Greeting response generated: '{greeting_response}'")
    # ---------------- LOCAL LLM --------------------

    # ---------------- OPENROUTER LLM -----------------
    response = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("master", greeting_prompt))
    if response.status_code == 200:
        greeting_response = response.json()["choices"][0]["message"]["content"]
        greeting_response = json.loads(greeting_response)
        logging.info(f"(OPEN ROUTER) Greetings raw response: '{greeting_response}'")
    else:
        logging.error(f"(OPEN ROUTER) Master Agent(Greetings) failed to provide a response: {response.status_code} - {response.text}")
        return {"master_agent_error": RETRY_ERROR}
    # ---------------- OPENROUTER LLM -----------------

    return greeting_response

def generate_availability_question():
    """
    Uses the LLM to dynamically generate a question about the user's availability.
    """
    prompt = generate_availability_question_prompt()

    # ---------------- LOCAL LLM --------------------
    # response = llm_agent_b.invoke(prompt).strip()
    # response = json.loads(response)
    # logging.info(f"Generated Availability Question: {response}")
    # ---------------- LOCAL LLM --------------------

    # ---------------- OPENROUTER LLM -----------------
    response = requests.post(OPEN_ROUTER_API_URL, headers=OPEN_ROUTER_HEADERS, json=open_router_data("b", prompt))
    if response.status_code == 200:
        response = response.json()["choices"][0]["message"]["content"]
        response = json.loads(response)
        logging.info(f"(OPEN ROOUTER) Agent B Generate Availability Question raw response: '{response}'")
    else:
        logging.error(f"(OPEN ROOUTER) Agent B Generate Availability Question failed to provide a response: {response.status_code} - {response.text}")
        return {"agent_b_error": RETRY_ERROR}
     # ---------------- OPENROUTER LLM -----------------

    return response