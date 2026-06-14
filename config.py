"""config.py - Configuraciones globales y variables de entorno."""

import os
import json
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

# ── Rutas Base ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEMAS_DIR = os.path.join(BASE_DIR, "schemas")

# Asegurar que las carpetas existan
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCHEMAS_DIR, exist_ok=True)

# ── Configuraciones de LLM ─────────────────────────────
LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions")

# ── Carga de Esquemas ──────────────────────────────────
def load_tools_schema() -> list:
    """Carga el esquema JSON de herramientas para Qwen2.5."""
    schema_path = os.path.join(SCHEMAS_DIR, "tools_schema.json")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"❌ No se encontró el archivo de herramientas en: {schema_path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"❌ Error decodificando tools_schema.json: {e}")