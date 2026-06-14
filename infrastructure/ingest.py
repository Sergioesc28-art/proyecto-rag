# ingest.py — RAG con Detección de Cambios en Markdown
import os
import json
import hashlib
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb

# ── Rutas Base ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs") # <-- Cambiamos a docs
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
METADATA_FILE = os.path.join(DATA_DIR, "ingest_metadata.json")

# Aseguramos que la carpeta exista
os.makedirs(DOCS_DIR, exist_ok=True)

def calcular_hash_doc(ruta_doc: str) -> str:
    """Calcula el hash SHA256 de un archivo de texto."""
    sha256 = hashlib.sha256()
    with open(ruta_doc, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def cargar_metadata() -> dict:
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_metadata(metadata: dict) -> None:
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def doc_cambio(nombre_doc: str, hash_nuevo: str, metadata: dict) -> bool:
    if nombre_doc not in metadata:
        return True
    return hash_nuevo != metadata[nombre_doc].get('hash')

def load_markdowns(folder: str) -> dict:
    """Lee todos los archivos .md crudos de la carpeta."""
    archivos_md = {}
    if not os.path.exists(folder):
        print(f"⚠️  Carpeta '{folder}' no encontrada")
        return archivos_md
    
    for file in os.listdir(folder):
        if file.endswith(".md"):
            ruta_completa = os.path.join(folder, file)
            try:
                with open(ruta_completa, 'r', encoding='utf-8') as f:
                    archivos_md[file] = f.read()
            except Exception as e:
                print(f"⚠️  Error leyendo {file}: {e}")
    return archivos_md

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def indexar():
    print("=" * 70)
    print("📄 INGESTA INTELIGENTE DE MARKDOWN")
    print("=" * 70)
    
    print(f"\n1️⃣  Leyendo documentos de la carpeta '{DOCS_DIR}'...")
    archivos_md = load_markdowns(DOCS_DIR)
    
    if not archivos_md:
        print("   ❌ No se encontraron archivos .md. Abortando.")
        return
        
    print("\n2️⃣  Cargando metadata de ingesta anterior...")
    metadata = cargar_metadata()
    
    print("\n3️⃣  Conectando a ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name="documentos",
        metadata={"description": "Documentos de Yoyo Burguer"}
    )
    
    print("\n4️⃣  Verificando cambios en documentos...")
    docs_procesados, docs_omitidos, total_chunks = 0, 0, 0
    
    for nombre_doc, contenido in archivos_md.items():
        ruta_doc = os.path.join(DOCS_DIR, nombre_doc)
        hash_actual = calcular_hash_doc(ruta_doc)
        
        if not doc_cambio(nombre_doc, hash_actual, metadata):
            print(f"   ⏭️  {nombre_doc}: SIN CAMBIOS (omitido)")
            docs_omitidos += 1
            continue
            
        print(f"   🔄 {nombre_doc}: CAMBIOS DETECTADOS / NUEVO")
        
        if nombre_doc in metadata:
            collection.delete(where={"source_file": nombre_doc})
            
        chunks = chunk_text(contenido)
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(chunks).tolist()
        
        ids = [f"{nombre_doc}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"source_file": nombre_doc, "chunk_index": i, "ingestion_date": datetime.now().isoformat()}
            for i in range(len(chunks))
        ]
        
        collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        metadata[nombre_doc] = {
            "hash": hash_actual,
            "chunks_count": len(chunks),
            "ingestion_date": datetime.now().isoformat()
        }
        docs_procesados += 1
        total_chunks += len(chunks)
        
    print("\n5️⃣  Guardando metadata...")
    guardar_metadata(metadata)
    print("\n✅ INGESTA COMPLETADA")

if __name__ == "__main__":
    indexar()