from config import app, user_session, MIN_QUESTIONS, MAX_QUESTIONS, RETRY_ERROR, GENERAL_ERROR
from controllers.agents import classify_query, agent_a_answer, agent_b_followup, agent_b_score_response, agent_b_summarize_learning, agent_b_extract_key_elements, generate_availability_question, respond_greeting
from controllers.utils import filter_records_by_topics_and_user_level, find_relevant_topic_ids, find_relevant_user_level_ids

from flask import request, jsonify, render_template
import logging
from query_data import query_rag

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Session storage (Resets when a new query is received)
user_session = {}

### Routes ###
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    try:
        data = request.json
        user_query = data.get("input")
        logging.info(f"Received user input: {user_query}")

        if not user_query:
            logging.error("No input received from user.")
            return jsonify({"error": "Please enter a query."}), 400

        logging.info(f"User Session: {user_session}")
        # If a session is ongoing, use the same agent (Agent A or B)
        if "assigned_agent" in user_session:
            logging.info(f"Continuing session with Agent {user_session['assigned_agent']}.")
            return submit_response(user_query)
        
        # If a new query is detected, reset the session
        if user_session.get("conversation_ended", False):
            logging.info("New query detected. Resetting session...")
            user_session.clear()
        
        # Classify the query (Master Agent)
        classification = classify_query(user_query)
        logging.info(f"Master Agent classified the query as: {classification}")
        
        user_session.clear()
        user_session["conversation_ended"] = False  # Ensure conversation tracking resets
        
        if classification == "A":
            user_session["assigned_agent"] = "A"  # Store the assigned agent: A
            answer = agent_a_answer(user_query)
            return final_result(agent="A", answer=answer)

        elif classification == "B":
            followup_question = agent_b_followup(user_query) 

            if "agent_b_error" in followup_question:
                return jsonify({"retry_error": followup_question["agent_b_error"]}), 500
            
            user_session["assigned_agent"] = "B"  # Store the assigned agent: B
            logging.info(f"Agent B generated follow-up question: {followup_question}") 
            logging.info(f"Response Type: {type(followup_question)}")
            user_session.update({
                "query": user_query,
                "responses": [],
                "questions": [followup_question["question"]],  # Store the question as a list
                "question_count": 1,  # Start with 1 question (adjust dynamically later)
                "scores": []
            })
            return jsonify({"question": followup_question["question"], "answer_options": followup_question["suggested_answer"], "clear_input": True})  # Fixed response format
        
        elif classification == "GREET":
            answer = respond_greeting(user_query)
            logging.info(f"Greeting response: {answer}")
            return jsonify({
                "final_response": False,
                "greeting": True,
                "result": answer['greeting'],
                "answer_options": answer['suggested_quetions']})

        else:
            logging.error(f"Unexpected classification result: {classification}")
            return jsonify({"retry_error": RETRY_ERROR}), 500
        
    except Exception as e:
        user_session.clear()
        logging.error(f"Error in submit route: {e}")
        return jsonify({"error": GENERAL_ERROR}), 500

@app.route("/submit_response", methods=["POST"])
def submit_response(user_response):
    try:
        data = request.json
        logging.info(f"\n\n\nUser Session: {user_session}\n\n\n")
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
                logging.info(f"User Availability Recorded: {user_response}")  
                return final_result(agent="B")
            
            logging.info(f"Question Index: {question_index}")
            logging.info(f"User Session: {len(user_session["questions"])}")

            if question_index >= len(user_session["questions"]):
                return jsonify({"error": "Invalid question index."}), 400

            question = user_session["questions"][question_index]
            logging.info(f"Received user response: {user_response}")

            question_count = len(user_session["responses"])
            score, reasoning, more_questions_needed = agent_b_score_response(user_response, question, question_count)

            user_session["responses"].append(user_response)
            user_session["scores"].append({"response": user_response, "score": score, "reasoning": reasoning})
            
            next_question_count = question_count + 1
            # Force continue if under MIN_QUESTIONS
            if next_question_count < MIN_QUESTIONS:
                more_questions_needed = "Yes"
    
            # Force stop if at MAX_QUESTIONS
            elif next_question_count >= MAX_QUESTIONS:
                more_questions_needed = "No"

            logging.info(f"question_count: {question_count}, next_question_count: {next_question_count}, forced more_questions_needed: {more_questions_needed}")
            logging.info(f"Scored {question_count + 1}/{MAX_QUESTIONS}: {score} - {reasoning} - More Needed? {more_questions_needed}")

            # If max questions reached or no more questions needed → Final Response
            if next_question_count >= MAX_QUESTIONS or more_questions_needed == "No":
                if "availability" not in user_session:
                    next_question = generate_availability_question()  
                    user_session["questions"].append(next_question["question"])
                    user_session["availability"] = True 
                    return jsonify({"question": next_question["question"], "answer_options": next_question["suggested_answer"], "clear_input": True})
                    
            user_input_with_history = ""
            if len(user_session["responses"]) > 0:
                user_input_with_history += f"User: {user_session['query']}\n\n"
                for i, (response, question) in enumerate(zip(user_session["responses"], user_session["questions"])):
                    user_input_with_history += f"Assistant{i+1}: {question}\nUser{i+1}: {response}\n\n"
            next_question = agent_b_followup(user_input_with_history)

            if "agent_b_error" in next_question:
                user_session["responses"].pop()
                user_session["scores"].pop()
                return jsonify({"retry_error": next_question["agent_b_error"]}), 500
            user_session["questions"].append(next_question["question"])
            return jsonify({"question": next_question["question"], "answer_options": next_question["suggested_answer"], "clear_input": True})

        return jsonify({"error": "Unexpected behavior. Please state your query."}), 500
    
    except Exception as e:
        user_session.clear()
        logging.error(f"Error in submit_response route: {e}")
        return jsonify({"error": GENERAL_ERROR}), 500

def final_result(agent, answer=None):
    try:
        if agent == "A":
            if "assigned_agent" in user_session:
                del user_session["assigned_agent"]
            user_session["conversation_ended"] = True  # Mark conversation as ended
            logging.info(f"Answer: {answer}")

            if "agent_a_error" in answer:
                return jsonify({"retry_error": answer["agent_a_error"]}), 500
            else:
                return jsonify({
                "final_response": False,
                "greeting": False,
                "result": f"✅ Agent A: {answer["response"]}",
                "answer_options": answer["suggested_answer"]})  # Return Agent A's final result

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
            logging.info(f"RAG Response: {rag_response}")

            if "rag_error" in rag_response:
                return jsonify({"retry_error": rag_response["rag_error"]}), 500
            
            user_session["conversation_ended"] = True  # Mark conversation as ended
            user_session["availability"] = False 

            if "assigned_agent" in user_session:
                del user_session["assigned_agent"]

            score_breakdown = user_session["scores"]
            user_availability = user_session["user_availability"]
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
        
    except Exception as e:
        user_session.clear()
        logging.error(f"Error in final_result function: {e}")
        return jsonify({"error": GENERAL_ERROR}), 500

if __name__ == "__main__":
    app.run(debug=True)