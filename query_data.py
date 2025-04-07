import json
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from langchain.schema.document import Document
from dotenv import load_dotenv
import os

from get_embedding_function import get_embedding_function
from config import llm_agent_b, RETRY_ERROR
import random
import logging
from flask import session

CHROMA_PATH = "chroma"
load_dotenv()

# Set up Google Gemini LLM
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
llm = GoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GOOGLE_API_KEY)



PROMPT_TEMPLATE = """
You specialize in creating a structured, week-wise course based on the user's query.
Your goal is to design an engaging and progressive learning plan using only the provided resources.

### Instructions:
- Organize resources in a logical order (beginner → advanced).
- Ensure the output follows **valid JSON format**.
- Provide a brief introduction summarizing the course.
- Each **week** should include:
  - `title`: The title of the resource
  - `description`: A short description of the resource
  - `url`: The link to access the resource
  - `key_takeaways`: A list of key learning points from the resource
  - `suggested_exercises`: (Optional) Suggested exercises for hands-on learning

---

### Available Learning Resources:
{context}

---

### User Query:
{question}

---

### Expected JSON Output Format:

{{
  "course_title": "Generated Course Title",
  "introduction": "Brief course summary",
  "weeks": [
    {{
      "week": 1,
      "title": "Resource Title 1",
      "description": "Short description of Resource 1",
      "url": "https://example.com/resource-1",
      "key_takeaways": [
        "Key concept 1",
        "Key concept 2",
        "Key concept 3"
      ],
      "suggested_exercises": "Describe exercises or projects the student can try."
    }},
    {{
      "week": 2,
      "title": "Resource Title 2",
      "description": "Short description of Resource 2",
      "url": "https://example.com/resource-2",
      "key_takeaways": [
        "Key concept 1",
        "Key concept 2",
        "Key concept 3"
      ],
      "suggested_exercises": "Describe exercises or projects the student can try."
    }}
    // Additional weeks...
  ]
}}
"""


def query_rag(query_text: str, relevant_doc_ids: list):
    # Prepare the DB.
    try:
      embedding_function = get_embedding_function()
      db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

      print(f"\n\n\nDB: {db}\n\n\n")
      print(f"\n\n\nRelevant Doc IDs: {relevant_doc_ids}\n\n\n")
      all_docs = db.get()
      # filtered_docs = [
      #     (Document(page_content=doc, metadata=meta), 0)
      #     for doc, meta in zip(all_docs["documents"], all_docs["metadatas"])
      #     if any(str(topic_id) in meta.get("topics", "").split(",") for topic_id in relevant_topic_ids)
      # ]
      # for doc, meta in zip(all_docs["documents"], all_docs["metadatas"]):
          # print(f"\n\n-----\nMeta ID: {meta.get('id')}")
          # print(f"{type(meta.get('id'))}")

          # print(f"Relevant Doc IDs: {relevant_doc_ids}")
          # print(f"Meta ID in relevant_doc_ids: {meta.get('id') in relevant_doc_ids}\n\n----\n")
      filtered_docs = [
          (Document(page_content=doc, metadata=meta), 0)
          for doc, meta in zip(all_docs["documents"], all_docs["metadatas"])
          if meta.get("id") in relevant_doc_ids
      ]
      print(f"\nFiltered {len(filtered_docs)} documents.")
      print(f"\n Docs Filtered: {filtered_docs}")
      session["filteredDocs"] = serialize_filtered_docs_for_llm(filtered_docs)
      # Construct context text
      context_text = "\n\n---\n\n".join([doc[0].page_content for doc in filtered_docs])

      # Generate prompt
      prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
      prompt = prompt_template.format(context=context_text, question=query_text)
      # print(f"\n---------------PROMPT-----------------\n{prompt}\n----------------------------------------\n")

      # Test Snippet
      # random_bool = random.choice([True, True])
      # print("Random bool: ", random_bool)
      # if random_bool == True:
      #   response = '{ "category": "A }'
        # return {"rag_error": RETRY_ERROR}
      # else:
      # Invoke LLM
      #response_text = llm_agent_b.invoke(prompt) if llm_agent_b else "LLM not initialized."
      response_text = llm.invoke(prompt) if llm else "LLM not initialized."
      if "```" in response_text:
          response_text = response_text.split("```json")[1].split("```")[0].strip()

      response_text = json.loads(response_text)
      # Extract source metadata
      sources_id = [doc[0].metadata.get("id", None) for doc in filtered_docs]
      sources_links = [
          json.loads(doc[0].page_content).get("URL/Link", "No URL")
          for doc in filtered_docs
      ]

      # Print formatted response
      formatted_response = f"""
      \n\n---------------RESPONSE-----------------
      Response: {response_text}
      
      Sources IDs: {sources_id}
      
      Sources Links: {sources_links}
      ----------------------------------------
      """
      print(formatted_response)

    except Exception as e:
      logging.error(f"Error querying RAG: {e}")
      return {"rag_error": RETRY_ERROR}

    return response_text, sources_id, sources_links, filtered_docs

def serialize_filtered_docs_for_llm(filtered_docs):
    return [
        {
            "metadata": doc.metadata,
            "page_content": doc.page_content,
            "score": score
        }
        for doc, score in filtered_docs
    ]
# query_rag()