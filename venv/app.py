from flask import Flask, request, jsonify, render_template
from langchain_community.llms import Ollama
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Initialize Mistral model with Ollama
llm = Ollama(model="mistral")

MIN_QUESTIONS = 1
MAX_QUESTIONS = 1

# Global session storage
user_session = {
    "query": None,
    "responses": [],
    "questions": [],
    "question_count": 0,  # number of questions asked so far
}

def call_mistral(prompt, max_tokens=100, temperature=0.5):
    """Helper function to call Mistral LLM via Ollama."""
    logging.info("Calling Mistral with prompt: %s", prompt)
    try:
        response = llm.invoke(prompt)
        logging.info("Mistral response: %s", response)
        return response.strip() if response else ""
    except Exception as e:
        logging.error("Error with Mistral API: %s", e)
        return ""

def is_ai_ml(text):
    """Check if the text mentions AI/ML content."""
    keywords = ["ai", "artificial intelligence", "machine learning", "deep learning", "neural network", "data science", "ml"]
    result = any(kw in text.lower() for kw in keywords)
    logging.info("Checking if text is AI/ML related: %s -> %s", text, result)
    return result

def is_valid_followup_response(response, last_question):
    """Validate if the user's follow-up response is relevant to the follow-up question."""
    prompt = (
        f"Evaluate if the user's response addresses the follow-up question in the AI/ML domain.\n"
        f"Follow-up question: \"{last_question}\"\n"
        f"User response: \"{response}\"\n\n"
        "Final Answer: on-topic or off-topic."
    )
    classification = call_mistral(prompt, max_tokens=50, temperature=0.3)
    logging.info("Follow-up validation result: %s", classification)
    return "on-topic" in classification.lower() if classification else False

def generate_question(context):
    """Generate a concise follow-up question in the AI/ML domain."""
    logging.info("Generating follow-up question for context: %s", context)
    prompt = (
        f"Generate a concise follow-up question in the AI/ML domain based on the context: \"{context}\". "
        "The question should be friendly, help understand the user's background, and avoid repetition."
    )
    question = call_mistral(prompt, max_tokens=50, temperature=0.5) or "Could you share more about your experience with AI/ML?"
    logging.info("Generated question: %s", question)
    return question

def generate_summary(initial_query, responses):
    """Generate a summary sentence combining the initial query with all responses."""
    logging.info("Generating summary for query: %s with responses: %s", initial_query, responses)
    responses_text = " ".join(responses)
    prompt = (
        f"Summarize the user's AI/ML needs based on the following information:\n"
        f"Query: '{initial_query}'\nResponses: '{responses_text}'\n"
        "Provide a concise sentence summarizing what the user specifically wants in the AI/ML domain."
    )
    summary = call_mistral(prompt, max_tokens=100, temperature=0.5) or "Summary generation failed."
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
    result = call_mistral(prompt, max_tokens=100, temperature=0.5)
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

def score_responses(responses, questions):
    """Score all follow-up responses."""
    total_score = 0
    breakdown = []
    for i, response in enumerate(responses):
        question = questions[i] if i < len(questions) else "No corresponding question."
        score, explanation = score_response_with_context(response, question)
        total_score += score
        breakdown.append(f"Q{i+1}: Score {score}. Explanation: {explanation}")
    average_score = total_score / len(responses) if responses else 0
    return average_score, breakdown


def determine_user_level(average_score):
    """Determine user level based on average score."""
    logging.info("Determining user level for average score: %s", average_score)
    if average_score < 2.0:
        return "Beginner in the AI/ML domain."
    elif average_score < 3.5:
        return "Intermediate in the AI/ML domain."
    return "Advanced AI/ML practitioner with strong theoretical and practical experience."

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
        if not is_ai_ml(user_input):
            return jsonify({"message": "Please enter a query related to AI/ML."}), 400
        user_session.update({"query": user_input, "responses": [], "questions": [], "question_count": 1})
        first_question = generate_question(user_input)
        user_session["questions"].append(first_question)
        return jsonify({"question": first_question, "clear_input": True})

    last_question = user_session["questions"][-1] if user_session["questions"] else ""
    if not is_valid_followup_response(user_input, last_question):
        return jsonify({"message": "Response seems off-topic. Please answer in the context of AI/ML.", "clear_input": False}), 400

    user_session["responses"].append(user_input)
    user_session["question_count"] += 1

    # Check if the session has enough responses for scoring
    if user_session["question_count"] >= MAX_QUESTIONS or len(user_session["responses"]) >= MIN_QUESTIONS:

        avg_score, breakdown = score_responses(user_session["responses"], user_session["questions"])
        summary = generate_summary(user_session["query"], user_session["responses"])
        logging.info("Finalizing session. Score: %s, Summary: %s", avg_score, summary)
        return jsonify({
            "result": determine_user_level(avg_score),
            "average_score": avg_score,
            "breakdown": breakdown,
            "summary": summary,
            "responses": user_session["responses"]
        })

    next_question = generate_question(user_input)
    user_session["questions"].append(next_question)
    return jsonify({"question": next_question, "clear_input": True})

if __name__ == "__main__":
    app.run(debug=True)
