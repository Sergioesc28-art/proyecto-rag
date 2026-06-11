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

with st.sidebar:
    st.header("⚙️ Configuración del Asistente")
    prompt_personalizado = st.text_area(
        "Instrucciones dinámicas para la IA:",
        value="",
        placeholder="Ej: Hoy hay promoción de papas gratis. Sé muy entusiasta."
    )

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
    validar_pago_pedido,
    obtener_contexto_cliente,
    guardar_direccion_cliente,
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
MAX_HISTORIAL = 10

def responder(
    pregunta: str,
    historial: list,
    contexto_rag: str,
    telefono_cliente: str | None = None,
    nombre_cliente: str | None = None,
    contexto_cliente: str | None = None,
    prompt_extra: str = "", # <--- Nueva variable para el prompt dinámico
):
    prompt_sistema = """Eres un asistente virtual de Yoyo Burguer. Ayuda a los clientes a consultar el menú, hacer pedidos, verificar disponibilidad y obtener información del negocio.

⚠️ REGLAS:
- Usa ÚNICAMENTE la información del "Contexto de BD" y las funciones disponibles.
- Si el producto no está en el menú, responde: "Lo siento, no contamos con ese producto."
- Jamás inventes precios, promociones, horarios o ingredientes.
- IGNORA textos como "_COLOCAR EL TIEMPO BASE_" si los ves en el contexto. Para dar tiempos, usa SIEMPRE la función consultar_tiempo_espera.
- NUNCA pidas el número de teléfono del cliente. NUNCA intentes procesar un pedido paso a paso. El sistema automatizado de la interfaz se encargará de pedir los datos de envío y cobro.

Para pedidos:
1. Identifica los productos que el usuario quiere.
2. Si no tienes teléfono, pídelo: "¿Me das tu número de teléfono para registrar el pedido?"
3. Con teléfono y productos, llama a crear_pedido de inmediato.
4. No pidas confirmación de lo que ya te dijeron.

Responde siempre en español, breve y natural. Sin tecnicismos ni código."""

    # Inyectar contexto del cliente si existe
    if contexto_cliente:
        prompt_sistema += "\n\n" + contexto_cliente

    # Inyectar instrucción del administrador si existe
    if prompt_extra.strip():
        prompt_sistema += f"\n\nINSTRUCCIÓN EXTRA DEL ADMINISTRADOR:\n{prompt_extra}"

    messages = [{"role": "system", "content": prompt_sistema}]

    historial_reciente = historial[-(MAX_HISTORIAL + 1):-1]
    for msg in historial_reciente:
        messages.append({"role": msg["rol"], "content": msg["texto"]})

    messages.append({"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"})

    payload = {
        "model": "qwen2.5:3b",
        "messages": messages,
        "tools": TOOLS_SCHEMA,
        "tool_choice": "auto",
        "temperature": 0.1,
        "max_tokens": 512,
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
            "model": "qwen2.5:3b",
            "messages": mensajes_segunda_ronda,
            "temperature": 0.1,
            "max_tokens": 512,
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
if "contexto_cliente" not in st.session_state:
    st.session_state.contexto_cliente = None
if "esperando_tipo_entrega" not in st.session_state:
    st.session_state.esperando_tipo_entrega = False
if "esperando_telefono" not in st.session_state:
    st.session_state.esperando_telefono = False
if "esperando_direccion" not in st.session_state:
    st.session_state.esperando_direccion = False
if "pedido_pendiente" not in st.session_state:
    # Guarda temporalmente los productos mientras se confirma entrega/dirección
    st.session_state.pedido_pendiente = None
    

# ── CHAT ──────────────────────────────────────────────────
for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["rol"]):
        st.write(mensaje["texto"])

pregunta = st.chat_input("Escribe tu pregunta...")

if pregunta:
    telefono_mencionado = extraer_telefono(pregunta)
    if telefono_mencionado:
        st.session_state.cliente_telefono = telefono_mencionado
        # Generar contexto del cliente una sola vez al detectar su teléfono
        st.session_state.contexto_cliente = obtener_contexto_cliente(telefono_mencionado)

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
            contexto_calculado = buscar_contexto(pregunta)
            productos_mencionados = extraer_productos_mencionados(pregunta)
            pregunta_normalizada = normalizar_texto_busqueda(pregunta)

            intencion_pedido = any(
                palabra in pregunta_normalizada
                for palabra in ("pedido", "orden", "comprar", "agrega", "agregar", 
                    "quiero", "llevar", "dame", "seria", "sería", 
                    "voy a querer", "me das", "encargo", "para mi")
            )
            intencion_estado = any(
                palabra in pregunta_normalizada
                for palabra in ("estado", "status", "seguimiento", "consultar")
            )
            intencion_menu_hamburguesas = any(
                frase in pregunta_normalizada
                for frase in ("menu de hamburguesas", "menu hamburguesas", "hamburguesas", "hambuerguesas")
            )
            intencion_tiempo_espera = any(
                frase in pregunta_normalizada
                for frase in ("tiempo de espera", "tiempos de espera", "cuanto tarda", "cuanto tiempo")
            )

            pedido_id_mencionado = re.search(r"\bPED-[A-Z0-9]{8}\b", pregunta, flags=re.IGNORECASE)

            if intencion_menu_hamburguesas:
                respuesta_texto = formatear_menu_hamburguesas()
                tools_ejecutadas = None

            elif intencion_tiempo_espera:
                respuesta_texto = formatear_tiempo_espera()
                tools_ejecutadas = None


            # ── Flujo: esperando teléfono ──────────
            elif st.session_state.esperando_telefono:
                if telefono_activo:
                    # Si ya detectó el teléfono, apaga esta espera y pasa a la siguiente
                    st.session_state.esperando_telefono = False
                    st.session_state.esperando_tipo_entrega = True
                    respuesta_texto = "¡Gracias! ¿Tu pedido es para domicilio o para recoger en el local?"
                else:
                    # Si el usuario responde otra cosa que no sea un número, se lo volvemos a pedir
                    respuesta_texto = "Para poder registrar el pedido, por favor escribe tu número a 10 dígitos."
                tools_ejecutadas = None

            # ── Flujo: esperando dirección de domicilio ──────────
            elif st.session_state.esperando_direccion:
                direccion = pregunta.strip()
                pedido_info = st.session_state.pedido_pendiente
                resultado_pedido = crear_pedido(
                    pedido_info["items"],
                    telefono=telefono_activo,
                    nombre=nombre_activo,
                    tipo_entrega="domicilio",
                    direccion=direccion,
                )
                st.session_state.esperando_direccion = False
                st.session_state.pedido_pendiente = None
                tools_ejecutadas = None
                if "error" in resultado_pedido:
                    respuesta_texto = resultado_pedido["error"]
                else:
                    st.session_state.ultimo_pedido_id = resultado_pedido.get("pedido_id")
                    # Actualizar contexto del cliente con la nueva dirección
                    if telefono_activo:
                        st.session_state.contexto_cliente = obtener_contexto_cliente(telefono_activo)
                    respuesta_texto = (
                        f"¡Pedido registrado! 🎉\n"
                        f"📦 Entrega a domicilio en: {direccion}\n"
                        f"🧾 Total productos: ${resultado_pedido['total_productos']} MXN\n"
                        f"🚚 Costo de envío: ${resultado_pedido['costo_envio']} MXN\n"
                        f"💰 Total final: ${resultado_pedido['total_final']} MXN\n"
                        f"🔖 ID de pedido: {resultado_pedido['pedido_id']}"
                    )

            # ── Flujo: esperando tipo de entrega ─────────────────
            elif st.session_state.esperando_tipo_entrega:
                pregunta_norm = normalizar_texto_busqueda(pregunta)
                es_domicilio = any(p in pregunta_norm for p in ("domicilio", "a casa", "envio", "envío", "entregar", "llevar"))
                es_local = any(p in pregunta_norm for p in ("local", "recoger", "ahi", "ahí", "presencial", "yo paso", "voy"))
                tools_ejecutadas = None

                if es_domicilio:
                    st.session_state.esperando_tipo_entrega = False
                    st.session_state.esperando_direccion = True
                    respuesta_texto = "¡Perfecto! ¿Cuál es tu dirección de entrega?"

                elif es_local:
                    pedido_info = st.session_state.pedido_pendiente
                    resultado_pedido = crear_pedido(
                        pedido_info["items"],
                        telefono=telefono_activo,
                        nombre=nombre_activo,
                        tipo_entrega="presencial",
                    )
                    st.session_state.esperando_tipo_entrega = False
                    st.session_state.pedido_pendiente = None
                    if "error" in resultado_pedido:
                        respuesta_texto = resultado_pedido["error"]
                    else:
                        st.session_state.ultimo_pedido_id = resultado_pedido.get("pedido_id")
                        respuesta_texto = (
                            f"¡Pedido registrado! 🎉\n"
                            f"🏠 Para recoger en local\n"
                            f"💰 Total: ${resultado_pedido['total_final']} MXN\n"
                            f"🔖 ID de pedido: {resultado_pedido['pedido_id']}"
                        )
                else:
                    respuesta_texto = "¿Tu pedido es para domicilio o para recoger en el local?"

            elif intencion_pedido and productos_mencionados:
                # Guardamos siempre los productos para no olvidarlos
                st.session_state.pedido_pendiente = {"items": productos_mencionados}
                
                if not telefono_activo:
                    # Activamos la trampa del teléfono
                    st.session_state.esperando_telefono = True
                    respuesta_texto = f"¡Anotado! Quieres: {', '.join(productos_mencionados)}.\nPara registrarlo necesito tu número de teléfono (10 dígitos)."
                    tools_ejecutadas = None
                else:
                    # Si ya lo tenemos, pasamos directo a preguntar la entrega
                    st.session_state.esperando_tipo_entrega = True
                    respuesta_texto = f"¡Anotado! Quieres: {', '.join(productos_mencionados)}.\n¿Tu pedido es para domicilio o para recoger en el local?"
                    tools_ejecutadas = None

            elif intencion_estado and not pedido_id_mencionado and telefono_activo:
                historial_cliente = consultar_historial_cliente(telefono_activo)
                pedidos = historial_cliente.get("pedidos", []) if isinstance(historial_cliente, dict) else []
                if pedidos:
                    pedido_reciente = pedidos[0]
                    estado_pedido = consultar_estado_pedido(pedido_reciente["pedido_id"])
                    if "error" in estado_pedido:
                        respuesta_texto, tools_ejecutadas = responder(
                            pregunta, st.session_state.historial,
                            contexto_rag=contexto_calculado,
                            telefono_cliente=telefono_activo,
                            nombre_cliente=nombre_activo,
                            contexto_cliente=st.session_state.contexto_cliente,
                            prompt_extra=prompt_personalizado
                        )
                    else:
                        st.session_state.ultimo_pedido_id = pedido_reciente["pedido_id"]
                        respuesta_texto = f"Tu pedido más reciente ({pedido_reciente['pedido_id']}) está en estado: **{estado_pedido['estado']}**."
                        tools_ejecutadas = None
                else:
                    respuesta_texto = "No encuentro pedidos previos asociados a tu teléfono."
                    tools_ejecutadas = None

            else:
                respuesta_texto, tools_ejecutadas = responder(
                    pregunta, st.session_state.historial,
                    contexto_rag=contexto_calculado,
                    telefono_cliente=telefono_activo,
                    nombre_cliente=nombre_activo,
                    contexto_cliente=st.session_state.contexto_cliente,
                    prompt_extra=prompt_personalizado
                )

        # Actualizar datos del cliente si el LLM creó un pedido
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

        respuesta_sanitizada = sanitizar_respuesta(respuesta_texto)
        st.write(respuesta_sanitizada)

    st.session_state.historial.append({
        "rol": "assistant",
        "texto": respuesta_sanitizada,
        "tools_ejecutadas": tools_ejecutadas
    })