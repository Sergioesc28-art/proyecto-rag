from sentence_transformers import SentenceTransformer
import chromadb

# ── Conectar a ChromaDB ───────────────────────────────────
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="documentos")

# ── Modelo de embeddings ──────────────────────────────────
model = SentenceTransformer("all-MiniLM-L6-v2")

# ── Buscar contexto relevante ─────────────────────────────
def buscar_contexto(pregunta, top_k=5):
    embedding = model.encode([pregunta]).tolist()
    resultados = collection.query(
        query_embeddings=embedding,
        n_results=top_k
    )
    contexto = "\n\n".join(resultados["documents"][0])
    return contexto

# ── Prueba rápida ─────────────────────────────────────────
if __name__ == "__main__":
    pregunta = input("Escribe una pregunta: ")
    contexto = buscar_contexto(pregunta)
    print("\nContexto encontrado:\n")
    print(contexto)