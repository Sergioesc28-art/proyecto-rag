import streamlit as st
from sentence_transformers import SentenceTransformer
import chromadb

@st.cache_resource
def _get_chroma_collection():
    client = chromadb.PersistentClient(path="./chroma_db")
    return client.get_or_create_collection(name="documentos")

@st.cache_resource
def _get_embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

# FIX NUEVO: cachear el resultado del embedding por texto de pregunta.
# Si el usuario hace la misma pregunta (o una igual), no recalcula.
# ttl=300 → se limpia cada 5 minutos para no acumular memoria indefinidamente.
@st.cache_data(ttl=300)
def buscar_contexto(pregunta: str, top_k: int = 5) -> str:
    model = _get_embedding_model()
    collection = _get_chroma_collection()
    embedding = model.encode([pregunta]).tolist()
    resultados = collection.query(query_embeddings=embedding, n_results=top_k)
    return "\n\n".join(resultados["documents"][0])