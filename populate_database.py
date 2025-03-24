import json
import argparse
import os
import shutil
import pandas as pd
import json
from langchain.schema.document import Document
from get_embedding_function import get_embedding_function
from langchain.vectorstores.chroma import Chroma
from config import main_excel_file, main_sheet

CHROMA_PATH = "chroma"
DATA_PATH = main_excel_file #"Resources Version 3.xlsx"
MAIN_SHEET = main_sheet #"main"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    if args.reset:
        print("✨ Clearing Database")
        clear_database()

    documents, df = load_documents()
    add_to_chroma(documents, df)

def load_documents():
    df = pd.read_excel(DATA_PATH, sheet_name=MAIN_SHEET)
    documents = []
    for index, row in df.iterrows():
        if pd.notna(row.get("doc_id")):
            continue  # Skip rows that already have a doc_id
        doc = Document(page_content=json.dumps(row.to_dict()), metadata={"source": "main_sheet", "row_index": index})
        print(f"Row Added: {row}")
        documents.append(doc)
    
    # print(f"📄 Loaded documents:{documents}")
    return documents, df

def add_to_chroma(documents: list[Document], df: pd.DataFrame):
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=get_embedding_function())
    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])
    print(f"Number of existing documents in DB: {len(existing_ids)}")
    print(f"Existing IDs: {existing_ids}")

    new_documents = []
    # for doc in documents:
    #     doc_id = hash(doc.page_content)
    #     topics = json.loads(doc.page_content)["Topic"] 
    #     difficulty_level = json.loads(doc.page_content)["Difficulty Level"]

    #     print(f"Doc: {doc}")
    #     print(f"Checking doc_id: {doc_id}")
    #     print(f"Type of page_content: {type(doc.page_content)}")
    #     print(f"\n\n\nPage Content: {json.loads(doc.page_content)["Topic"]}\n\n\n")

    #     if doc_id not in existing_ids:
    #         print("In")
    #         doc.metadata["id"] = doc_id
    #         doc.metadata["topics"] = topics
    #         doc.metadata["difficulty_level"] = difficulty_level
    #         new_documents.append(doc)
    #         df.at[doc.metadata["row_index"], "doc_id"] = str(doc_id)

    for doc in documents:
        if not doc.page_content.strip():  # Avoid empty or blank content
            print(f"❌ Skipping empty content at row {doc.metadata['row_index']}")
            continue

        try:
            content_dict = json.loads(doc.page_content)
            doc_id = hash(doc.page_content)
            topics = content_dict.get("Topic")
            difficulty_level = content_dict.get("Difficulty Level")
        except Exception as e:
            print(f"❌ Error processing doc at row {doc.metadata['row_index']}: {e}")
            continue

        if doc_id not in existing_ids:
            doc.metadata["id"] = doc_id
            doc.metadata["topics"] = topics
            doc.metadata["difficulty_level"] = difficulty_level
            new_documents.append(doc)
            df.at[doc.metadata["row_index"], "doc_id"] = str(doc_id)

    # print(new_documents)
    if new_documents:
        print(f"👉 Adding new documents: {len(new_documents)}")
        i = 1
        print(f"New docs to add: {len(new_documents)}")
        for doc in new_documents:
            print(f"📄 Preview doc content: {doc.page_content[:100]}")

        db.add_documents(new_documents, ids=[str(doc.metadata["id"]) for doc in new_documents])
        db.persist()
        df.to_excel(DATA_PATH, sheet_name="main", index=False)
    else:
        print("✅ No new documents to add")

def clear_database():
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

if __name__ == "__main__":
    main()
