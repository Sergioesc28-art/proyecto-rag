import os
import streamlit as st
from sentence_transformers import SentenceTransformer
import chromadb

# Calcular la ruta absoluta a la carpeta 'data/chroma_db'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, "data", "chroma_db")

@st.cache_resource
def _get_chroma_collection():
    """Conecta con ChromaDB de forma persistente. Se cachea para no saturar memoria."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name="documentos")

@st.cache_resource
def _get_embedding_model():
    """Carga el modelo de NLP. Se cachea porque es costoso computacionalmente."""
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_data(ttl=300)
def buscar_contexto(pregunta: str, top_k: int = 5) -> str:
    """
    Convierte la pregunta en vector, busca en ChromaDB y retorna los documentos.
    El resultado se guarda en caché por 5 minutos (ttl=300) por si el usuario repite la pregunta.
    """
    model = _get_embedding_model()
    collection = _get_chroma_collection()
    
    embedding = model.encode([pregunta]).tolist()
    resultados = collection.query(query_embeddings=embedding, n_results=top_k)
    
    # Previene errores si no hay resultados en la DB
    if not resultados.get("documents") or not resultados["documents"][0]:
        return "No hay información en los documentos."
        
    return "\n\n".join(resultados["documents"][0])