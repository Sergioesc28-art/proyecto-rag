import streamlit as st
import requests
import json
import traceback

# ── Configuración de página ───────────────────────────────
st.set_page_config(
    page_title="Yoyo's IA",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Yoyo's IA")
st.caption("Sistema RAG + Function Calling con Llama 3.2 8B")

# ── Importar búsqueda vectorial y funciones ───────────────
from query import buscar_contexto
from functions import (
    consultar_menu,
    verificar_disponibilidad,
    consultar_ingredientes,
    crear_pedido,
    consultar_estado_pedido,
    cancelar_pedido,
    aplicar_descuento,
    consultar_tiempo_espera,
    registrar_cliente,
    consultar_historial_cliente,
    obtener_informacion_yoyo,
    obtener_complementos
)

LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"

# ── Cargar tools_schema.json ───────────────────────────────
with open("tools_schema.json", "r", encoding="utf-8") as f:
    TOOLS_SCHEMA = json.load(f)

# ── Mapeo de funciones para ejecución ──────────────────────
FUNCIONES_DISPONIBLES = {
    "consultar_menu": consultar_menu,
    "verificar_disponibilidad": verificar_disponibilidad,
    "consultar_ingredientes": consultar_ingredientes,
    "crear_pedido": crear_pedido,
    "consultar_estado_pedido": consultar_estado_pedido,
    "cancelar_pedido": cancelar_pedido,
    "aplicar_descuento": aplicar_descuento,
    "consultar_tiempo_espera": consultar_tiempo_espera,
    "registrar_cliente": registrar_cliente,
    "consultar_historial_cliente": consultar_historial_cliente,
    "obtener_informacion_yoyo": obtener_informacion_yoyo,
    "obtener_complementos": obtener_complementos,
}


# ── Ejecutor de herramientas ───────────────────────────────
def ejecutar_funcion(nombre_funcion: str, argumentos: dict) -> dict:
    """
    Ejecuta una función del sistema con los argumentos proporcionados.
    
    Args:
        nombre_funcion: Nombre de la función a ejecutar.
        argumentos: Dict con parámetros.
    
    Returns:
        dict con resultado o error.
    """
    if nombre_funcion not in FUNCIONES_DISPONIBLES:
        return {
            "error": f"Función '{nombre_funcion}' no existe.",
            "funciones_disponibles": list(FUNCIONES_DISPONIBLES.keys())
        }
    
    try:
        funcion = FUNCIONES_DISPONIBLES[nombre_funcion]
        resultado = funcion(**argumentos)
        return {"exito": True, "resultado": resultado}
    
    except Exception as e:
        return {
            "error": f"Error ejecutando {nombre_funcion}: {str(e)}",
            "traceback": traceback.format_exc()
        }


# ── Función para llamar a Llama CON TOOL CALLING ──────────
def responder(pregunta: str, contexto_rag: str = None):
    """
    Llama a Llama 3.2 8B con:
    1. Contexto RAG (búsqueda vectorial)
    2. Tools schema (funciones disponibles)
    
    Retorna respuesta final después de ejecutar herramientas si es necesario.
    """
    
    # Si no hay contexto RAG, buscar primero
    if contexto_rag is None:
        contexto_rag = buscar_contexto(pregunta)
    
    prompt_sistema = """Eres un asistente de Yoyo Burguer que ayuda a clientes a:
- Consultar el menú
- Hacer pedidos
- Verificar disponibilidad
- Registrarse como cliente
- Obtener información del negocio

Usa las funciones disponibles para responder preguntas sobre:
✓ Menú y precios
✓ Disponibilidad de productos
✓ Ingredientes
✓ Pedidos (crear, consultar, cancelar)
✓ Descuentos
✓ Clientes y historial

Si el usuario pide algo que pueda resolver con una función, ÚSALA.
Si no puede resolverse con funciones, usa el contexto RAG.
Siempre sé amable y útil."""

    # ── Primer llamado a Llama CON tools ──
    payload = {
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"}
        ],
        "tools": TOOLS_SCHEMA,
        "tool_choice": "auto",
        "max_tokens": 1024,
        "stream": False
    }
    
    try:
        respuesta = requests.post(LLAMA_URL, json=payload, timeout=60)
        resultado_inicial = respuesta.json()
        
    except Exception as e:
        return f"❌ Error conectando con Llama: {e}", None
    
    # ── Procesar respuesta ────────────────────────────────
    mensaje_respuesta = resultado_inicial["choices"][0]["message"]
    
    # Si hay tool_calls, ejecutarlas
    if "tool_calls" in mensaje_respuesta:
        tool_calls = mensaje_respuesta["tool_calls"]
        resultados_tools = []
        
        for tool_call in tool_calls:
            nombre_herramienta = tool_call["function"]["name"]
            args_json = tool_call["function"]["arguments"]
            
            # Parsear argumentos (puede ser string o dict)
            if isinstance(args_json, str):
                argumentos = json.loads(args_json)
            else:
                argumentos = args_json
            
            # Ejecutar función
            resultado_ejecucion = ejecutar_funcion(nombre_herramienta, argumentos)
            resultados_tools.append({
                "tool_name": nombre_herramienta,
                "arguments": argumentos,
                "result": resultado_ejecucion
            })
        
        # ── Segundo llamado a Llama CON resultados de tools ──
        mensajes_segunda_ronda = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"},
            mensaje_respuesta
        ]
        
        # Agregar resultados de tools
        for tool_result in resultados_tools:
            mensajes_segunda_ronda.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_name"],
                "content": json.dumps(tool_result["result"], ensure_ascii=False)
            })
        
        # Llamar Llama nuevamente para que genere respuesta final
        payload_segunda = {
            "messages": mensajes_segunda_ronda,
            "max_tokens": 1024,
            "stream": False
        }
        
        try:
            respuesta_final = requests.post(LLAMA_URL, json=payload_segunda, timeout=60)
            resultado_final = respuesta_final.json()
            texto_respuesta = resultado_final["choices"][0]["message"]["content"]
        except Exception as e:
            texto_respuesta = f"Error en segunda llamada a Llama: {e}"
        
        return texto_respuesta, resultados_tools
    
    else:
        # Sin tool_calls, retornar respuesta directo
        texto_respuesta = mensaje_respuesta.get("content", "Sin respuesta")
        return texto_respuesta, None

# ── Historial de conversación ─────────────────────────────
if "historial" not in st.session_state:
    st.session_state.historial = []

# ── Columnas para mejor visualización ──────────────────────
col_chat, col_tools = st.columns([3, 1])

# ── Input del usuario ─────────────────────────────────────
with col_chat:
    pregunta = st.chat_input("Escribe tu pregunta...")

# ── Mostrar historial ─────────────────────────────────────
for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["rol"]):
        st.write(mensaje["texto"])
        
        # Si hay resultados de tools, mostrarlos
        if "tools_ejecutadas" in mensaje and mensaje["tools_ejecutadas"]:
            with st.expander("🔧 Herramientas ejecutadas"):
                for tool in mensaje["tools_ejecutadas"]:
                    st.write(f"**Función**: `{tool['tool_name']}`")
                    st.write(f"**Parámetros**: {tool['arguments']}")
                    if "error" in tool["result"]:
                        st.error(f"Error: {tool['result']['error']}")
                    elif tool["result"].get("exito"):
                        st.json(tool["result"]["resultado"])

# ── Procesar pregunta ─────────────────────────────────────
if pregunta:
    # Mostrar pregunta del usuario
    with st.chat_message("user"):
        st.write(pregunta)
    st.session_state.historial.append({
        "rol": "user",
        "texto": pregunta,
        "tools_ejecutadas": None
    })

    # Generar respuesta con tool calling
    with st.chat_message("assistant"):
        with st.spinner("Procesando (RAG + Function Calling)..."):
            respuesta_texto, tools_ejecutadas = responder(pregunta)
        
        st.write(respuesta_texto)
        
        # Mostrar herramientas ejecutadas si las hay
        if tools_ejecutadas:
            with st.expander("🔧 Herramientas ejecutadas en esta respuesta"):
                for tool in tools_ejecutadas:
                    st.write(f"**Función**: `{tool['tool_name']}`")
                    st.write(f"**Parámetros**: {tool['arguments']}")
                    if "error" in tool["result"]:
                        st.error(f"❌ {tool['result']['error']}")
                    elif tool["result"].get("exito"):
                        st.success("✅ Ejecución exitosa")
                        st.json(tool["result"]["resultado"])
        
        # Mostrar contexto RAG usado
        contexto_rag = buscar_contexto(pregunta)
        with st.expander("📚 Contexto RAG utilizado"):
            st.text(contexto_rag)
    
    # Guardar en historial
    st.session_state.historial.append({
        "rol": "assistant",
        "texto": respuesta_texto,
        "tools_ejecutadas": tools_ejecutadas
    })

# ── Panel lateral con info del sistema ──────────────────────
with st.sidebar:
    st.markdown("### ℹ️ Información del Sistema")
    st.write(f"**Modelo**: Llama 3.2 8B Q4_K_M")
    st.write(f"**URL**: {LLAMA_URL}")
    st.write(f"**Herramientas disponibles**: {len(FUNCIONES_DISPONIBLES)}")
    
    st.markdown("### 🔧 Funciones disponibles")
    for nombre in FUNCIONES_DISPONIBLES.keys():
        st.write(f"- `{nombre}`")