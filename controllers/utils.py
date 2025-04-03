from config import (
    main_excel_file,
    topic_ids_excel_file,
    user_level_ids_excel_file,
    main_sheet,
    main_topic_ids_col,
    main_user_level_col,
    main_chromadb_doc_id_col,
    topicids_col,
    topicids_value_col,
)
from config import llm_agent_b
from controllers.prompts import find_relevant_topic_ids_prompt, find_relevant_user_level_ids_prompt, extract_key_elements_prompt

import pandas as pd
import logging
import re
import sys



### Read Topic IDs from Excel ###
def get_topic_ids():
    df = pd.read_excel(topic_ids_excel_file, sheet_name="topic_ids")
    df = df.sample(n=6)
    return dict(zip(df[topicids_col], df[topicids_value_col]))

### Find Relevant Topic IDs ###
def find_relevant_topic_ids(summary):
    topic_dict = get_topic_ids()
    topics_str = "\n".join([f"{topic}: {topic_id}" for topic, topic_id in topic_dict.items()])
    prompt = find_relevant_topic_ids_prompt(summary, topics_str)
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

### Read User Level IDs from Excel ###
def get_user_level_ids():
    df = pd.read_excel(user_level_ids_excel_file, sheet_name="user_level_ids")
    return dict(zip(df["User Level"], df["ID"]))

### Find User Level ID ###
def find_relevant_user_level_ids(user_level):
    user_level_dict = get_user_level_ids()
    levels_str = "\n".join([f"{level}: {level_id}" for level, level_id in user_level_dict.items()])
    
    prompt = find_relevant_user_level_ids_prompt(user_level, levels_str)

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

    logging.error("Could not extract a valid user level ID.")
    return None

### Filter Relevant Resources ###
def filter_records_by_topics_and_user_level(relevant_topic_ids, user_level_id):
    df = pd.read_excel(main_excel_file, sheet_name=main_sheet)

    # Convert stored IDs to proper format
    df[main_topic_ids_col] = df[main_topic_ids_col].apply(
        lambda x: [int(i.strip()) for i in str(x).split(',') if i.strip().isdigit()]
    )
    df[main_user_level_col] = df[main_user_level_col].apply(
        lambda x: [int(i.strip()) for i in str(x).split(',') if i.strip().isdigit()]
    )

    logging.info(f"Relevant Topic IDs: {relevant_topic_ids}")
    logging.info(f"User Level ID: {user_level_id}")

    # Apply filtering
    filtered_df = df[
        df[main_topic_ids_col].apply(lambda record: any(num in record for num in relevant_topic_ids)) &
        df[main_user_level_col].apply(lambda record: user_level_id in record)
    ]

    logging.info(f"Filtered {len(filtered_df)} documents.") 
    return filtered_df[main_chromadb_doc_id_col].values.tolist()


### Extract Key Elements for RAG ###
def extract_key_elements(summary, user_level):
    prompt = extract_key_elements_prompt(summary, user_level)
    return llm_agent_b.invoke(prompt).strip().split(", ")