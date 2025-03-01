from langchain_community.vectorstores import Chroma

# Path to your ChromaDB directory (replace if different)
CHROMA_PATH = "./chroma_db"  # Update if your db is elsewhere

# Load the database
db = Chroma(persist_directory=CHROMA_PATH)

# Get total documents
total_docs = db._collection.count()
print(f"Total documents in ChromaDB: {total_docs}")

# Retrieve and print some example documents
docs = db.similarity_search("Python", k=5)  # Search for relevant docs

for i, doc in enumerate(docs, 1):
    print(f"\nDocument {i}:")
    print(doc.page_content)
    print("Metadata:", doc.metadata)