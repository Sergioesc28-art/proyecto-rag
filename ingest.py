# ingest.py — RAG con Detección de Cambios en PDFs
# Sistema inteligente que detecta si PDFs fueron modificados
# evita duplicados y mantiene metadata limpia en ChromaDB

import os
import json
import hashlib
from datetime import datetime
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb

# Archivo donde guardamos hashes de PDFs procesados
METADATA_FILE = "ingest_metadata.json"


# ── 1. Calcular hash SHA256 del PDF ────────────────────────
def calcular_hash_pdf(ruta_pdf: str) -> str:
    """
    Calcula el hash SHA256 del contenido de un PDF.
    Sirve para detectar si el archivo cambió desde la última ingesta.
    
    Args:
        ruta_pdf: Ruta al archivo PDF.
    
    Returns:
        String con hash SHA256 en hexadecimal.
    """
    sha256 = hashlib.sha256()
    with open(ruta_pdf, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


# ── 2. Cargar metadata de PDFs previamente procesados ──────────
def cargar_metadata() -> dict:
    """
    Lee el archivo ingest_metadata.json que contiene
    información de PDFs ya procesados (hash, fecha, etc).
    
    Returns:
        dict con estructura: {"menu.pdf": {"hash": "...", "fecha": "...", ...}}
    """
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# ── 3. Guardar metadata actualizada ────────────────────────────
def guardar_metadata(metadata: dict) -> None:
    """
    Persiste la metadata de PDFs procesados a disco.
    
    Args:
        metadata: dict con información de PDFs.
    """
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


# ── 4. Verificar si PDF cambió ─────────────────────────────────
def pdf_cambio(nombre_pdf: str, hash_nuevo: str, metadata: dict) -> bool:
    """
    Determina si un PDF fue modificado comparando hashes.
    
    Args:
        nombre_pdf: Nombre del archivo (ej: "menu.pdf").
        hash_nuevo: Hash SHA256 actual del archivo.
        metadata: dict con PDFs previamente procesados.
    
    Returns:
        True si el PDF es nuevo o cambió, False si es idéntico.
    """
    if nombre_pdf not in metadata:
        # PDF nunca fue procesado antes
        return True
    
    hash_anterior = metadata[nombre_pdf].get('hash')
    cambio_detectado = hash_nuevo != hash_anterior
    
    return cambio_detectado


# ── 5. Leer PDFs y extraer texto ───────────────────────────────
def load_pdfs(folder: str) -> dict:
    """
    Lee todos los PDFs de una carpeta y retorna
    un diccionario con nombre del archivo y su contenido.
    
    Args:
        folder: Carpeta donde están los PDFs (ej: "pdfs").
    
    Returns:
        dict con estructura: {"menu.pdf": "texto...", "operaciones.pdf": "texto..."}
    """
    archivos_pdf = {}
    
    if not os.path.exists(folder):
        print(f"⚠️  Carpeta '{folder}' no encontrada")
        return archivos_pdf
    
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            ruta_completa = os.path.join(folder, file)
            try:
                reader = PdfReader(ruta_completa)
                texto = ""
                for num_pagina, page in enumerate(reader.pages, 1):
                    contenido = page.extract_text()
                    if contenido:
                        # Agregar metainformación de página
                        texto += f"\n--- Página {num_pagina} ---\n{contenido}"
                
                archivos_pdf[file] = texto
                
            except Exception as e:
                print(f"⚠️  Error leyendo {file}: {e}")
    
    return archivos_pdf


# ── 6. Fragmentar texto con overlap ────────────────────────────
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """
    Divide un texto en fragmentos con overlap.
    Overlap permite que información en límites de chunks no se pierda.
    
    Args:
        text: Texto a fragmentar.
        chunk_size: Tamaño de cada fragmento (caracteres).
        overlap: Sobreposición entre fragmentos (caracteres).
    
    Returns:
        Lista de strings (chunks).
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        
        if chunk.strip():  # Solo agregar si no está vacío
            chunks.append(chunk)
        
        start += chunk_size - overlap
    
    return chunks


# ── 7. Indexar con metadata inteligente ────────────────────────
def indexar():
    """
    Realiza ingesta inteligente de PDFs a ChromaDB:
    1. Lee PDFs de la carpeta "pdfs"
    2. Calcula hash de cada uno
    3. Si PDF cambió: elimina vectores viejos, agrega nuevos
    4. Si PDF es igual: salta (no reindexa)
    5. Guarda metadata con fecha y hash
    """
    
    print("=" * 70)
    print("📄 INGESTA INTELIGENTE DE PDFs (Sistema con Detección de Cambios)")
    print("=" * 70)
    
    # ── Paso 1: Leer PDFs actuales ──
    print("\n1️⃣  Leyendo PDFs de la carpeta 'pdfs'...")
    archivos_pdf = load_pdfs("pdfs")
    
    if not archivos_pdf:
        print("   ❌ No se encontraron PDFs. Abortando.")
        return
    
    print(f"   ✓ {len(archivos_pdf)} PDF(s) encontrado(s)")
    for nombre in archivos_pdf.keys():
        print(f"     • {nombre}")
    
    # ── Paso 2: Cargar metadata anterior ──
    print("\n2️⃣  Cargando metadata de ingesta anterior...")
    metadata = cargar_metadata()
    print(f"   ✓ {len(metadata)} PDF(s) previamente procesado(s)")
    
    # ── Paso 3: Conectar a ChromaDB ──
    print("\n3️⃣  Conectando a ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(
        name="documentos",
        metadata={"description": "Documentos de Yoyo Burguer con metadata"}
    )
    print(f"   ✓ Conectado. Colección tiene {collection.count()} vectores")
    
    # ── Paso 4: Procesar cada PDF ──
    print("\n4️⃣  Verificando cambios en PDFs...")
    pdfs_procesados = 0
    pdfs_omitidos = 0
    total_chunks = 0
    
    for nombre_pdf, contenido in archivos_pdf.items():
        # Calcular hash actual
        ruta_pdf = os.path.join("pdfs", nombre_pdf)
        hash_actual = calcular_hash_pdf(ruta_pdf)
        
        # Verificar si cambió
        if not pdf_cambio(nombre_pdf, hash_actual, metadata):
            print(f"\n   ⏭️  {nombre_pdf}: SIN CAMBIOS (omitido)")
            pdfs_omitidos += 1
            continue
        
        if nombre_pdf in metadata:
            print(f"\n   🔄 {nombre_pdf}: CAMBIOS DETECTADOS")
        else:
            print(f"\n   ✨ {nombre_pdf}: NUEVO")
        
        # ── Eliminar vectores viejos (si existen) ──
        if nombre_pdf in metadata:
            print(f"      → Eliminando {metadata[nombre_pdf].get('chunks_count', 0)} vectores viejos...")
            collection.delete(
                where={"source_file": nombre_pdf}
            )
        
        # ── Fragmentar texto ──
        chunks = chunk_text(contenido, chunk_size=500, overlap=100)
        print(f"      → Generando {len(chunks)} fragmentos...")
        
        # ── Generar embeddings ──
        print(f"      → Calculando embeddings...")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(chunks).tolist()
        
        # ── Preparar IDs y metadata ──
        ids = [f"{nombre_pdf.replace('.pdf', '')}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source_file": nombre_pdf,
                "chunk_index": i,
                "chunk_size": len(chunk),
                "ingestion_date": datetime.now().isoformat()
            }
            for i, chunk in enumerate(chunks)
        ]
        
        # ── Agregar a ChromaDB ──
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        
        # ── Actualizar metadata ──
        metadata[nombre_pdf] = {
            "hash": hash_actual,
            "chunks_count": len(chunks),
            "ingestion_date": datetime.now().isoformat(),
            "status": "procesado"
        }
        
        pdfs_procesados += 1
        total_chunks += len(chunks)
        print(f"      ✅ Agregados {len(chunks)} vectores a ChromaDB")
    
    # ── Paso 5: Guardar metadata ──
    print("\n5️⃣  Guardando metadata actualizada...")
    guardar_metadata(metadata)
    print(f"   ✓ {METADATA_FILE} actualizado")
    
    # ── Resumen final ──
    print("\n" + "=" * 70)
    print("✅ INGESTA COMPLETADA")
    print("=" * 70)
    print(f"📊 Resumen:")
    print(f"   • PDFs procesados: {pdfs_procesados}")
    print(f"   • PDFs omitidos (sin cambios): {pdfs_omitidos}")
    print(f"   • Total de vectores agregados: {total_chunks}")
    print(f"   • Total de vectores en ChromaDB: {collection.count()}")
    print("=" * 70)


if __name__ == "__main__":
    indexar()