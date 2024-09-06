from langchain_openai import OpenAIEmbeddings

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from app.services.retrievers import get_parent_retriever

embeddings = OpenAIEmbeddings(
    openai_api_key=OPENAI_API_KEY,
    model="text-embedding-3-large")

# See docker command above to launch a postgres instance with pgvector enabled.
connection = "postgresql+psycopg2://vector_search:slegka328doljanelegka@127.0.0.1:5209/postgres" # Uses psycopg3!

# connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"
collection_name = "my_docs"


vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)



vector_store.delete_collection()




