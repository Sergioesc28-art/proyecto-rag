import streamlit as st
import requests
import json
import traceback
import os
import re
import unicodedata

# ── Configuración de página ───────────────────────────────
st.set_page_config(
    page_title="Yoyo's IA",
    layout="wide"
)

st.title("Yoyo's IA")
st.info("Para crear y consultar pedidos, comparte tu número de teléfono una sola vez. Lo guardaré durante la conversación para no volver a pedirlo.")


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
            "error": f"La acción '{nombre_funcion}' no existe.",
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


# ── Sanitizador de respuesta final ─────────────────────────
def sanitizar_respuesta(texto: str) -> str:
    reemplazos = {
        r'\b(función|herramienta|tool|API|tool_call|JSON|parámetros)\b': ''
    }
    texto_limpio = texto
    for patron, reemplazo in reemplazos.items():
        texto_limpio = re.sub(patron, reemplazo, texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    return texto_limpio


def extraer_telefono(texto: str) -> str | None:
    coincidencia = re.search(r"(?<!\d)(\d{10})(?!\d)", texto)
    if coincidencia:
        return coincidencia.group(1)
    return None


def extraer_nombre_cliente(texto: str) -> str | None:
    patrones = [
        r"(?:mi nombre es|me llamo|soy)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:\s+[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+){0,3})",
    ]
    for patron in patrones:
        coincidencia = re.search(patron, texto, flags=re.IGNORECASE)
        if coincidencia:
            nombre = coincidencia.group(1).strip()
            return re.sub(r"\s+", " ", nombre)
    return None


def normalizar_texto_busqueda(texto: str) -> str:
    texto_normalizado = unicodedata.normalize("NFKD", texto.lower())
    texto_sin_acentos = "".join(caracter for caracter in texto_normalizado if not unicodedata.combining(caracter))
    texto_filtrado = re.sub(r"[^a-z0-9\s]", " ", texto_sin_acentos)
    return re.sub(r"\s+", " ", texto_filtrado).strip()


def extraer_productos_mencionados(texto: str) -> list[str]:
    # FIX 3: consultar_menu() ya tiene @st.cache_data en functions.py,
    # por lo que esta llamada no golpea SQLite en cada request.
    menu = consultar_menu()
    productos = menu["hamburguesas"] + menu["hot_dogs"] + menu["complementos"]
    texto_normalizado = normalizar_texto_busqueda(texto)

    encontrados: list[str] = []
    for producto in productos:
        nombre_normalizado = normalizar_texto_busqueda(producto["nombre"])
        if nombre_normalizado and nombre_normalizado in texto_normalizado:
            encontrados.append(producto["nombre"])
    return encontrados


def formatear_menu_hamburguesas() -> str:
    menu = consultar_menu()
    hamburguesas = menu["hamburguesas"]
    lineas = ["Hamburguesas disponibles en Yoyo Burguer:"]
    for producto in hamburguesas:
        disponibilidad = "Disponible" if producto["disponible"] else "No disponible"
        lineas.append(f"- {producto['nombre']} - ${producto['precio_base']} MXN - {disponibilidad}")
    return "\n".join(lineas)


def formatear_tiempo_espera() -> str:
    espera = consultar_tiempo_espera()
    return (
        f"Tiempo estimado de espera: {espera['minutos_espera']} minutos. "
        f"Hay {espera['pedidos_activos']} pedido(s) activo(s). "
        f"Cálculo: 5 minutos base + 4 minutos por pedido activo."
    )


# ── Llamada a Llama con herramientas ──────────────────────
# FIX 4: se limita el historial a los últimos MAX_HISTORIAL mensajes
# para que el prompt no crezca indefinidamente con cada turno.
MAX_HISTORIAL = 10

def responder(
    pregunta: str,
    historial: list,
    contexto_rag: str,                      # FIX 2: ahora es obligatorio, siempre se recibe desde afuera
    telefono_cliente: str | None = None,
    nombre_cliente: str | None = None,
):
    # contexto_rag ya viene calculado desde el bloque principal,
    # por lo que NO se vuelve a llamar buscar_contexto() aquí.

    prompt_sistema = """Eres un asistente virtual automatizado y estricto de Yoyo Burguer. 

Tu objetivo es ayudar a los clientes a:
- Consultar el menú
- Hacer pedidos
- Verificar disponibilidad
- Registrarse como cliente
- Obtener información del negocio

⚠️ REGLA DE ORO DE SEGURIDAD (ANTI-ALUCINACIÓN):
- Básate ÚNICAMENTE en la información proporcionada en el "Contexto de BD" y en las funciones del sistema.
- Si el usuario te pide un producto, ingrediente o servicio que NO está explícitamente en el menú o en el contexto, debes responder amablemente: "Lo siento, no contamos con ese producto en nuestro menú actual".
- Jamás inventes precios, promociones, horarios, ingredientes o respuestas que no estén respaldadas por la base de datos.
- No asumas nada fuera de lo que se te ha entregado textualmente.

Si el usuario quiere hacer un pedido, tu objetivo es llamar a la función `crear_pedido`.
Para ello, sigue estos pasos de forma proactiva:
1. Identifica los productos que el usuario quiere en su pedido a partir de la conversación.
2. Verifica si tienes un número de teléfono. Un pedido necesita un cliente. Revisa el historial de la conversación para ver si el usuario ya lo ha proporcionado.
3. Si no tienes el teléfono, pídelo amablemente. Di algo como: "¡Claro! Para registrar tu pedido, ¿me podrías dar tu número de teléfono, por favor?".
4. Una vez que tengas el teléfono y los productos, actúa. No vuelvas a preguntar. Llama a la función `crear_pedido` con los productos. Si el usuario ya dio su teléfono en esta conversación, reutilízalo siempre.
5. No dudes ni pidas confirmación de nuevo sobre lo que ya te dijeron. Asume que la información que te dan es para que la uses.

Nunca menciones nombres internos de funciones, herramientas, JSON, parámetros ni pasos técnicos.
Nunca le indiques al usuario que escriba un comando o que use un flujo interno.
Si una consulta puede resolverse con una acción interna, ejecútala sin explicarla.
Si no puede resolverse con acciones internas, usa el contexto RAG.
Responde siempre en español claro, breve y natural.
No muestres código, pseudocódigo, JSON, ni instrucciones técnicas.
No uses lenguaje de programación como `const`, `await`, `console.log` o similar.
Siempre sé amable y útil."""

    messages = [{"role": "system", "content": prompt_sistema}]

    # FIX 4: solo enviamos los últimos MAX_HISTORIAL mensajes al LLM,
    # excluyendo el último que es la pregunta actual (que se agrega abajo).
    historial_reciente = historial[-(MAX_HISTORIAL + 1):-1]
    for msg in historial_reciente:
        messages.append({"role": msg["rol"], "content": msg["texto"]})

    # Pregunta actual con el contexto RAG ya calculado
    messages.append({"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"})

    payload = {
        "model": "mistral",
        "messages": messages,
        "tools": TOOLS_SCHEMA,
        "tool_choice": "auto",
        "temperature": 0.1,
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

            if nombre_herramienta == "crear_pedido":
                if telefono_cliente and not argumentos.get("telefono"):
                    argumentos["telefono"] = telefono_cliente
                if nombre_cliente and not argumentos.get("nombre"):
                    argumentos["nombre"] = nombre_cliente

            resultado_ejecucion = ejecutar_funcion(nombre_herramienta, argumentos)
            resultados_tools.append({
                "tool_name": nombre_herramienta,
                "arguments": argumentos,
                "result": resultado_ejecucion
            })

        mensajes_segunda_ronda = messages + [mensaje_respuesta]

        for tool_result in resultados_tools:
            mensajes_segunda_ronda.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_name"],
                "content": json.dumps(tool_result["result"], ensure_ascii=False)
            })

        payload_segunda = {
            "model": "mistral",
            "messages": mensajes_segunda_ronda,
            "temperature": 0.1,
            "max_tokens": 1024,
            "stream": False
        }

        try:
            # FIX 5: timeout reducido a 60s. 300s era demasiado sin feedback al usuario.
            respuesta_final = requests.post(LLAMA_URL, json=payload_segunda, timeout=60)
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

if "cliente_telefono" not in st.session_state:
    st.session_state.cliente_telefono = None

if "cliente_nombre" not in st.session_state:
    st.session_state.cliente_nombre = None

if "ultimo_pedido_id" not in st.session_state:
    st.session_state.ultimo_pedido_id = None

# ── Creación de columnas en la interfaz ────────────────────
col_chat, col_tools = st.columns([3, 1])

# ── LÓGICA DE LA COLUMNA DEL CHAT (Izquierda) ──────────────
with col_chat:
    # 1. Mostrar historial guardado PRIMERO
    for mensaje in st.session_state.historial:
        with st.chat_message(mensaje["rol"]):
            st.write(mensaje["texto"])

            if "tools_ejecutadas" in mensaje and mensaje["tools_ejecutadas"]:
                with st.expander("🔧 Acciones ejecutadas"):
                    for tool in mensaje["tools_ejecutadas"]:
                        st.write(f"**Parámetros**: {tool['arguments']}")
                        if "error" in tool["result"]:
                            st.error(f"Error: {tool['result']['error']}")
                        elif tool["result"].get("exito"):
                            st.json(tool["result"]["resultado"])

    # 2. El input del usuario se coloca DESPUÉS del historial
    pregunta = st.chat_input("Escribe tu pregunta...")

    # 3. Procesar la nueva pregunta si existe
    if pregunta:
        telefono_mencionado = extraer_telefono(pregunta)
        if telefono_mencionado:
            st.session_state.cliente_telefono = telefono_mencionado

        nombre_mencionado = extraer_nombre_cliente(pregunta)
        if nombre_mencionado:
            st.session_state.cliente_nombre = nombre_mencionado

        telefono_activo = st.session_state.cliente_telefono
        nombre_activo = st.session_state.cliente_nombre

        with st.chat_message("user"):
            st.write(pregunta)

        st.session_state.historial.append({
            "rol": "user",
            "texto": pregunta,
            "tools_ejecutadas": None
        })

        with st.chat_message("assistant"):
            with st.spinner("Procesando..."):

                # FIX 2: buscar_contexto() se llama UNA SOLA VEZ aquí.
                # Se guarda en contexto_calculado y se reutiliza en todo el bloque,
                # incluyendo la llamada a responder() y el expander de RAG al final.
                contexto_calculado = buscar_contexto(pregunta)

                productos_mencionados = extraer_productos_mencionados(pregunta)
                pregunta_normalizada = normalizar_texto_busqueda(pregunta)

                intencion_pedido = any(
                    palabra in pregunta_normalizada
                    for palabra in ("pedido", "orden", "comprar", "agrega", "agregar", "quiero", "llevar")
                )
                intencion_estado = any(
                    palabra in pregunta_normalizada
                    for palabra in ("estado", "status", "seguimiento", "consultar")
                )
                intencion_menu_hamburguesas = any(
                    frase in pregunta_normalizada
                    for frase in (
                        "menu de hamburguesas",
                        "menu hamburguesas",
                        "menu de hambuerguesas",
                        "menu hambuerguesas",
                        "hamburguesas",
                        "hambuerguesas",
                    )
                )
                intencion_tiempo_espera = any(
                    frase in pregunta_normalizada
                    for frase in (
                        "tiempo de espera",
                        "tiempos de espera",
                        "cuanto tarda",
                        "cuanto tiempo",
                        "dura la peticion",
                    )
                )

                pedido_id_mencionado = re.search(r"\bPED-[A-Z0-9]{8}\b", pregunta, flags=re.IGNORECASE)

                if intencion_menu_hamburguesas:
                    respuesta_texto = formatear_menu_hamburguesas()
                    tools_ejecutadas = [{
                        "tool_name": "consultar_menu",
                        "arguments": {},
                        "result": {"exito": True, "resultado": consultar_menu()}
                    }]

                elif intencion_tiempo_espera:
                    respuesta_texto = formatear_tiempo_espera()
                    tools_ejecutadas = [{
                        "tool_name": "consultar_tiempo_espera",
                        "arguments": {},
                        "result": {"exito": True, "resultado": consultar_tiempo_espera()}
                    }]

                elif intencion_pedido and productos_mencionados:
                    if not telefono_activo:
                        respuesta_texto = "Para registrar tu pedido necesito tu número de teléfono una sola vez."
                        tools_ejecutadas = None
                    else:
                        resultado_pedido = crear_pedido(productos_mencionados, telefono=telefono_activo, nombre=nombre_activo)
                        if "error" in resultado_pedido:
                            respuesta_texto = resultado_pedido["error"]
                            tools_ejecutadas = [{
                                "tool_name": "crear_pedido",
                                "arguments": {"items": productos_mencionados, "telefono": telefono_activo, "nombre": nombre_activo},
                                "result": resultado_pedido,
                            }]
                        else:
                            st.session_state.ultimo_pedido_id = resultado_pedido.get("pedido_id")
                            respuesta_texto = f"Pedido registrado con éxito. Total: ${resultado_pedido['total_final']} MXN."
                            tools_ejecutadas = [{
                                "tool_name": "crear_pedido",
                                "arguments": {"items": productos_mencionados, "telefono": telefono_activo, "nombre": nombre_activo},
                                "result": {"exito": True, "resultado": resultado_pedido}
                            }]

                elif intencion_estado and not pedido_id_mencionado and telefono_activo:
                    historial_cliente = consultar_historial_cliente(telefono_activo)
                    pedidos = historial_cliente.get("pedidos", []) if isinstance(historial_cliente, dict) else []

                    if pedidos:
                        pedido_reciente = pedidos[0]
                        estado_pedido = consultar_estado_pedido(pedido_reciente["pedido_id"])
                        if "error" in estado_pedido:
                            # Si falla, caemos al LLM pasando el contexto ya calculado
                            respuesta_texto, tools_ejecutadas = responder(
                                pregunta,
                                st.session_state.historial,
                                contexto_rag=contexto_calculado,
                                telefono_cliente=telefono_activo,
                                nombre_cliente=nombre_activo,
                            )
                        else:
                            st.session_state.ultimo_pedido_id = pedido_reciente["pedido_id"]
                            respuesta_texto = f"Tu pedido más reciente está en estado {estado_pedido['estado']}."
                            tools_ejecutadas = [{
                                "tool_name": "consultar_estado_pedido",
                                "arguments": {"pedido_id": pedido_reciente["pedido_id"]},
                                "result": {"exito": True, "resultado": estado_pedido}
                            }]
                    else:
                        respuesta_texto = "No encuentro un pedido previo asociado a ese teléfono."
                        tools_ejecutadas = None

                else:
                    # Caso general: pasa el contexto ya calculado, sin recalcularlo
                    respuesta_texto, tools_ejecutadas = responder(
                        pregunta,
                        st.session_state.historial,
                        contexto_rag=contexto_calculado,
                        telefono_cliente=telefono_activo,
                        nombre_cliente=nombre_activo,
                    )

            # ── Actualizar estado del pedido si aplica ────────
            if tools_ejecutadas:
                for tool in tools_ejecutadas:
                    if tool["tool_name"] == "crear_pedido" and tool["result"].get("exito"):
                        resultado_tool = tool["result"].get("resultado", {})
                        if isinstance(resultado_tool, dict):
                            st.session_state.ultimo_pedido_id = resultado_tool.get("pedido_id")
                            if resultado_tool.get("cliente_telefono"):
                                st.session_state.cliente_telefono = resultado_tool.get("cliente_telefono")
                            if resultado_tool.get("cliente_nombre"):
                                st.session_state.cliente_nombre = resultado_tool.get("cliente_nombre")

            # ── Mostrar respuesta ─────────────────────────────
            respuesta_sanitizada = sanitizar_respuesta(respuesta_texto)
            st.write(respuesta_sanitizada)

            if tools_ejecutadas:
                with st.expander("🔧 Acciones ejecutadas en esta respuesta"):
                    for tool in tools_ejecutadas:
                        st.write(f"**Parámetros**: {tool['arguments']}")
                        if "error" in tool["result"]:
                            st.error(f"❌ {tool['result']['error']}")
                        elif tool["result"].get("exito"):
                            st.success("✅ Ejecución exitosa")
                            st.json(tool["result"]["resultado"])

            # FIX 2: reutiliza contexto_calculado, NO llama buscar_contexto() de nuevo
            with st.expander("📚 Contexto RAG utilizado"):
                st.text(contexto_calculado)

        st.session_state.historial.append({
            "rol": "assistant",
            "texto": respuesta_sanitizada,
            "tools_ejecutadas": tools_ejecutadas
        })