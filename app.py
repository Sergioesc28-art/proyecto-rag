import streamlit as st
import requests
import json
import traceback
import os

# ── Configuración de página ───────────────────────────────
st.set_page_config(
    page_title="Yoyo's IA",
    layout="wide"
)

st.title("Yoyo's IA")
st.caption("Sistema RAG + Function Calling con Llama 3.2 8B")

# ── Importar búsqueda vectorial y funciones ───────────────
from database import init_database
from query import buscar_contexto
from functions import (
    consultar_menu,
    verificar_disponibilidad,
    consultar_ingredientes,
    crear_pedido,
    consultar_estado_pedido,
    cancelar_pedido,
    consultar_tiempo_espera,
    registrar_cliente,
    consultar_historial_cliente,
    obtener_informacion_yoyo,
    obtener_complementos,
    validar_pago_pedido
)

init_database()


LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions")

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
    "consultar_tiempo_espera": consultar_tiempo_espera,
    "registrar_cliente": registrar_cliente,
    "consultar_historial_cliente": consultar_historial_cliente,
    "obtener_informacion_yoyo": obtener_informacion_yoyo,
    "obtener_complementos": obtener_complementos,
    "validar_pago_pedido": validar_pago_pedido,
}


# ── Ejecutor de herramientas ───────────────────────────────
def ejecutar_funcion(nombre_funcion: str, argumentos: dict) -> dict:
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
✓ Pedidos (crear, consultar, cancelar, validar pago)
✓ Clientes y historial

Si el usuario pide algo que pueda resolver con una función, ÚSALA.
Si no puede resolverse con funciones, usa el contexto RAG.
Responde siempre en español claro, breve y natural.
No muestres código, pseudocódigo, JSON, ni instrucciones técnicas.
No uses lenguaje de programación como `const`, `await`, `console.log` o similar.
Si el usuario necesita hacer un pedido, explícale el paso de forma simple y práctica.
Siempre sé amable y útil."""

    payload = {
        "model": "mistral",
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
        respuesta = requests.post(LLAMA_URL, json=payload, timeout=120)
        resultado_inicial = respuesta.json()
    except Exception as e:
        return f"❌ Error conectando con Llama: {e}", None
    
    if "choices" not in resultado_inicial or not resultado_inicial["choices"]:
        error_msg = resultado_inicial.get("error", {}).get("message", str(resultado_inicial))
        return f"❌ Error de Ollama: {error_msg}", None
    
    mensaje_respuesta = resultado_inicial["choices"][0]["message"]
    
    if "tool_calls" in mensaje_respuesta:
        tool_calls = mensaje_respuesta["tool_calls"]
        resultados_tools = []
        
        for tool_call in tool_calls:
            nombre_herramienta = tool_call["function"]["name"]
            args_json = tool_call["function"]["arguments"]
            
            if isinstance(args_json, str):
                argumentos = json.loads(args_json)
            else:
                argumentos = args_json
            
            resultado_ejecucion = ejecutar_funcion(nombre_herramienta, argumentos)
            resultados_tools.append({
                "tool_name": nombre_herramienta,
                "arguments": argumentos,
                "result": resultado_ejecucion
            })
        
        mensajes_segunda_ronda = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"},
            mensaje_respuesta
        ]
        
        for tool_result in resultados_tools:
            mensajes_segunda_ronda.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_name"],
                "content": json.dumps(tool_result["result"], ensure_ascii=False)
            })
        
        payload_segunda = {
            "model": "mistral",
            "messages": mensajes_segunda_ronda,
            "max_tokens": 1024,
            "stream": False
        }
        
        try:
            respuesta_final = requests.post(LLAMA_URL, json=payload_segunda, timeout=120)
            resultado_final = respuesta_final.json()
            texto_respuesta = resultado_final["choices"][0]["message"]["content"]
        except Exception as e:
            texto_respuesta = f"Error en segunda llamada a Llama: {e}"
        
        return texto_respuesta, resultados_tools
    
    else:
        texto_respuesta = mensaje_respuesta.get("content", "Sin respuesta")
        return texto_respuesta, None


# ── Historial de conversación ─────────────────────────────
if "historial" not in st.session_state:
    st.session_state.historial = []

# ── Creación de columnas en la interfaz ────────────────────
col_chat, col_tools = st.columns([3, 1])

# ── LÓGICA DE LA COLUMNA DEL CHAT (Izquierda) ──────────────
with col_chat:
    # 1. Mostrar historial guardado PRIMERO
    for mensaje in st.session_state.historial:
        with st.chat_message(mensaje["rol"]):
            st.write(mensaje["texto"])
            
            if "tools_ejecutadas" in mensaje and mensaje["tools_ejecutadas"]:
                with st.expander("🔧 Herramientas ejecutadas"):
                    for tool in mensaje["tools_ejecutadas"]:
                        st.write(f"**Función**: `{tool['tool_name']}`")
                        st.write(f"**Parámetros**: {tool['arguments']}")
                        if "error" in tool["result"]:
                            st.error(f"Error: {tool['result']['error']}")
                        elif tool["result"].get("exito"):
                            st.json(tool["result"]["resultado"])

    # 2. El Input del usuario se coloca DESPUÉS del historial para que quede abajo
    pregunta = st.chat_input("Escribe tu pregunta...")

    # 3. Procesar la nueva pregunta si existe
    if pregunta:
        with st.chat_message("user"):
            st.write(pregunta)
        
        st.session_state.historial.append({
            "rol": "user",
            "texto": pregunta,
            "tools_ejecutadas": None
        })

        with st.chat_message("assistant"):
            with st.spinner("Procesando (RAG + Function Calling)..."):
                respuesta_texto, tools_ejecutadas = responder(pregunta)
            
            st.write(respuesta_texto)
            
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
            
            contexto_rag = buscar_contexto(pregunta)
            with st.expander("📚 Contexto RAG utilizado"):
                st.text(contexto_rag)
        
        st.session_state.historial.append({
            "rol": "assistant",
            "texto": respuesta_texto,
            "tools_ejecutadas": tools_ejecutadas
        })

# ── LÓGICA DE LA COLUMNA DE HERRAMIENTAS (Derecha) ─────────
with col_tools:
    st.subheader("🛠️ Panel de Control")
    st.info("Aquí puedes ver logs o configuraciones adicionales en tiempo real.")