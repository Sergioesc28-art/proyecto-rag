"""app.py - Orquestador principal de Yoyo Burguer IA."""

import streamlit as st
import re
import unicodedata

# ── Configuración Inicial de la Página (Debe ser el primer comando) ──
st.set_page_config(page_title="Yoyo's IA", layout="wide")

# ── Importaciones de la Arquitectura Modular ──
from config import load_tools_schema
from infrastructure.database import init_database
from infrastructure.query import buscar_contexto

from ui.sidebar import render_sidebar
from ui.chat_components import (
    render_header, render_chat_history, 
    display_user_message, render_loading_spinner,
    render_tarjetas_historial
)

from core.state_manager import inicializar_estado, EstadoConversacion, resetear_flujo_pedido
from core.prompt_manager import construir_prompt_sistema
from core.llm_service import generar_respuesta_llm_stream, sanitizar_respuesta

from services.customer_service import obtener_contexto_cliente
from services.tool_registry import ejecutar_herramienta
from services.order_service import crear_pedido, consultar_tiempo_espera
from services.menu_service import consultar_menu

# ── Inicialización de Dependencias ──
init_database()
TOOLS_SCHEMA = load_tools_schema()
inicializar_estado()

# ── Utilidades Locales de Texto ───────────────────────────────────────────
def normalizar_texto(texto: str) -> str:
    texto_norm = unicodedata.normalize("NFKD", texto.lower())
    texto_sin_acentos = "".join(c for c in texto_norm if not unicodedata.combining(c))
    texto_filtrado = re.sub(r"[^a-z0-9\s]", " ", texto_sin_acentos)
    texto_filtrado = texto_filtrado.replace("burguer", "burger").replace("hotdog", "hot dog")
    return re.sub(r"\s+", " ", texto_filtrado).strip()

def extraer_telefono(texto: str) -> str | None:
    coincidencia = re.search(r"(?<!\d)(\d{10})(?!\d)", texto)
    return coincidencia.group(1) if coincidencia else None

def formatear_menu_completo() -> str:
    menu = consultar_menu()
    lineas = ["🍔 **MENÚ DE YOYO BURGUER** 🍔\n"]
    for categoria, emoji in [("hamburguesas", "🍔"), ("hot_dogs", "🌭"), ("complementos", "🍟")]:
        if menu.get(categoria):
            lineas.append(f"{emoji} **{categoria.replace('_', ' ').title()}:**")
            for p in menu[categoria]:
                disp = "" if p["disponible"] else " *(🚫 Agotado)*"
                lineas.append(f"- **{p['nombre']}** | ${p['precio_base']} MXN{disp}")
            lineas.append("")
    return "\n".join(lineas)

def extraer_productos_mencionados(texto: str) -> list[str]:
    """Extrae productos usando un diccionario de alias para capturar nombres coloquiales."""
    txt_norm = normalizar_texto(texto)
    encontrados = set()
    
    # Mapeo de alias coloquiales a nombres oficiales de catálogo
    alias_menu = {
        "sencilla": "Hamburguesa Sencilla",
        "doble": "Hamburguesa Doble Carne",
        "doble carne": "Hamburguesa Doble Carne",
        "hawaiana": "Hamburguesa Hawaiana",
        "hamburguesa especial": "Hamburguesa Especial",
        "especial doble": "Hamburguesa Especial Doble Carne",
        "natsu": "Natsu Burger",
        "hot dog sencillo": "Hot Dog Sencillo",
        "jocho sencillo": "Hot Dog Sencillo",
        "hot dog hawaiano": "Hot Dog Hawaiano",
        "jocho hawaiano": "Hot Dog Hawaiano",
        "hot dog especial": "Hot Dog Especial",
        "jocho especial": "Hot Dog Especial",
        "papas": "Papas a la francesa",
        "francesas": "Papas a la francesa",
        "salchichas": "Salchichas tipo pulpo",
        "pulpos": "Salchichas tipo pulpo",
        "salchipulpos": "Salchichas tipo pulpo"
    }

    # Búsqueda por palabra exacta mediante límites de palabra (Regex)
    for alias, nombre_oficial in alias_menu.items():
        if re.search(rf"\b{alias}\b", txt_norm):
            encontrados.add(nombre_oficial)

    # Búsqueda estricta de respaldo por si escriben el nombre completo
    menu = consultar_menu()
    productos = menu["hamburguesas"] + menu["hot_dogs"] + menu["complementos"]
    for p in productos:
        if normalizar_texto(p["nombre"]) in txt_norm:
            encontrados.add(p["nombre"])

    return list(encontrados)

# ── Renderizado de UI Estática ───────────────────────────────────────────
render_header()
render_sidebar(fetch_context_callback=obtener_contexto_cliente)
render_chat_history()

# ── Bucle Principal de Conversación ──────────────────────────────────────
pregunta = st.chat_input("Escribe tu pregunta...")

if pregunta:
    display_user_message(pregunta)
    pregunta_norm = normalizar_texto(pregunta)
    
    # Referencias rápidas al estado actual de la sesión
    tel_activo = st.session_state.cliente_telefono
    nom_activo = st.session_state.cliente_nombre
    estado_actual = st.session_state.estado_conversacion

    with render_loading_spinner():
        respuesta_texto = ""
        tools_ejecutadas = None
        es_respuesta_estatica = True 

        # ── MÁQUINA DE ESTADOS: FLUJOS ACTIVOS DE TRANSACCIÓN ──
        if estado_actual == EstadoConversacion.ESPERANDO_CONFIRMACION_CONTACTO:
            # Agregamos "sip" y "sipi" a la lista para mayor cobertura
            es_afirmacion = any(p in pregunta_norm for p in ("si", "sip", "sipi", "claro", "ok", "va", "simon", "perfecto"))
            es_negacion = any(p in pregunta_norm for p in ("no", "otro", "cambiar"))
            posible_numero = extraer_telefono(pregunta)

            # Detectar si el usuario incluyó el tipo de entrega en el mismo mensaje
            es_domicilio_adelantado = any(p in pregunta_norm for p in ("domicilio", "casa", "envio", "llevar"))
            es_local_adelantado = any(p in pregunta_norm for p in ("local", "recoger", "presencial", "ahi", "voy"))

            if posible_numero or es_afirmacion:
                st.session_state.numero_contacto_final = posible_numero if posible_numero else tel_activo
                
                # Guardamos el número en una variable segura antes del reseteo de la máquina de estados
                contacto_usado = st.session_state.numero_contacto_final 
                
                # Caso adelantado 1: El usuario confirmó número y dijo que es en el local
                if es_local_adelantado:
                    res_pedido = crear_pedido(
                        st.session_state.pedido_pendiente["items"],
                        telefono=tel_activo, nombre=nom_activo, tipo_entrega="presencial",
                        numero_contacto=contacto_usado
                    )
                    resetear_flujo_pedido()
                    if "error" in res_pedido:
                        respuesta_texto = res_pedido["error"]
                    else:
                        st.session_state.ultimo_pedido_id = res_pedido.get("pedido_id")
                        respuesta_texto = (f"¡Pedido registrado! 🎉\n🏠 Para recoger en local\n"
                                           f"📞 Contacto: {contacto_usado}\n"
                                           f"💰 Total: ${res_pedido['total_final']} MXN\n🍔 ¡Gracias por tu compra!")
                
                # Caso adelantado 2: El usuario confirmó número y dijo que quiere a domicilio
                elif es_domicilio_adelantado:
                    st.session_state.estado_conversacion = EstadoConversacion.ESPERANDO_DIRECCION
                    respuesta_texto = "¡Anotado! ¿Cuál es tu dirección de entrega?"
                
                # Flujo normal: solo confirmó número de contacto
                else:
                    st.session_state.estado_conversacion = EstadoConversacion.ESPERANDO_TIPO_ENTREGA
                    respuesta_texto = "¡Perfecto!\n¿Tu pedido es para domicilio o para recoger en el local?"
            
            elif es_negacion:
                respuesta_texto = "Entendido. Por favor, escribe aquí el nuevo número de 10 dígitos al que debemos comunicarnos."
            else:
                respuesta_texto = f"No entendí bien. ¿Nos comunicaremos al número de cuenta ({tel_activo})? (Responde Sí/No o escribe un número nuevo)."

        elif estado_actual == EstadoConversacion.ESPERANDO_TIPO_ENTREGA:
            es_domicilio = any(p in pregunta_norm for p in ("domicilio", "casa", "envio", "llevar"))
            es_local = any(p in pregunta_norm for p in ("local", "recoger", "ahi", "presencial", "voy"))

            if es_domicilio:
                st.session_state.estado_conversacion = EstadoConversacion.ESPERANDO_DIRECCION
                respuesta_texto = "¡Perfecto! ¿Cuál es tu dirección de entrega?"
            elif es_local:
                contacto_usado = st.session_state.numero_contacto_final
                res_pedido = crear_pedido(
                    st.session_state.pedido_pendiente["items"],
                    telefono=tel_activo, nombre=nom_activo, tipo_entrega="presencial",
                    numero_contacto=contacto_usado
                )
                resetear_flujo_pedido() 
                if "error" in res_pedido:
                    respuesta_texto = res_pedido["error"]
                else:
                    st.session_state.ultimo_pedido_id = res_pedido.get("pedido_id")
                    respuesta_texto = (f"¡Pedido registrado! 🎉\n🏠 Para recoger en local\n"
                                       f"📞 Contacto: {contacto_usado}\n" 
                                       f"💰 Total: ${res_pedido['total_final']} MXN\n🍔 ¡Gracias por tu compra!")
            else:
                respuesta_texto = "¿Tu pedido es para domicilio o para recoger en el local?"

        elif estado_actual == EstadoConversacion.ESPERANDO_DIRECCION:
            contacto_usado = st.session_state.numero_contacto_final
            res_pedido = crear_pedido(
                st.session_state.pedido_pendiente["items"],
                telefono=tel_activo, nombre=nom_activo, tipo_entrega="domicilio",
                direccion=pregunta.strip(), numero_contacto=contacto_usado
            )
            resetear_flujo_pedido()
            if "error" in res_pedido:
                respuesta_texto = res_pedido["error"]
            else:
                st.session_state.ultimo_pedido_id = res_pedido.get("pedido_id")
                if tel_activo:
                    st.session_state.contexto_cliente = obtener_contexto_cliente(tel_activo)
                respuesta_texto = (f"¡Pedido registrado! 🎉\n📦 Entrega en: {res_pedido['direccion']}\n"
                                   f"🧾 Total productos: ${res_pedido['total_productos']} MXN\n"
                                   f"🚚 Costo envío: ${res_pedido['costo_envio']} MXN\n"
                                   f"💰 Total final: ${res_pedido['total_final']} MXN\n🍔 ¡Gracias por tu compra!")

        # ── DETECCIÓN DE INTENCIONES GENERALES (Fase de Escaneo Pre-LLM) ──
        else:
            palabras_pedido = (
                "pedido", "comprar", "quiero", "dame", "me gustaria", "me gustaría", 
                "orden", "ordeno", "para mi", "llevo", "llevar", "encargo", 
                "voy a querer", "me das", "agrega"
            )
            intencion_pedido = any(p in pregunta_norm for p in palabras_pedido)
            intencion_menu = any(p in pregunta_norm for p in ("menu", "carta", "productos", "que vendes", "tienen", "venden"))
            intencion_tiempo = any(p in pregunta_norm for p in ("tiempo de espera", "cuanto tarda", "demora"))
            productos_mencionados = extraer_productos_mencionados(pregunta)

            if intencion_menu:
                respuesta_texto = formatear_menu_completo()
            
            elif intencion_tiempo:
                tiempo_info = consultar_tiempo_espera()
                respuesta_texto = tiempo_info["mensaje"]

            elif intencion_pedido and productos_mencionados:
                if not tel_activo:
                    respuesta_texto = "Para registrar tu pedido, por favor ingresa primero tu **número de cuenta (10 dígitos)** en el panel lateral 👈."
                else:
                    st.session_state.pedido_pendiente = {"items": productos_mencionados}
                    st.session_state.estado_conversacion = EstadoConversacion.ESPERANDO_CONFIRMACION_CONTACTO
                    respuesta_texto = f"¡Anotado! Quieres: {', '.join(productos_mencionados)}.\n¿El número **{tel_activo}** será el método principal para comunicarnos contigo sobre este pedido?"
            
            # ── DELEGACIÓN CONTROLADA AL LLM (QWEN2.5 VIA STREAMING SSE) ──
            else:
                es_respuesta_estatica = False 
                contexto_rag = buscar_contexto(pregunta)
                prompt_sys = construir_prompt_sistema(
                    contexto_cliente=st.session_state.contexto_cliente,
                    pedido_pendiente=st.session_state.pedido_pendiente
                )
                
                generador_respuesta, tools_ejecutadas = generar_respuesta_llm_stream(
                    pregunta=pregunta,
                    historial=st.session_state.historial,
                    contexto_rag=contexto_rag,
                    prompt_sistema=prompt_sys,
                    tools_schema=TOOLS_SCHEMA,
                    ejecutor_herramientas=ejecutar_herramienta,
                    telefono_cliente=tel_activo,
                    nombre_cliente=nom_activo
                )

                if tools_ejecutadas:
                    for t in tools_ejecutadas:
                        if t["tool_name"] == "crear_pedido" and t["result"].get("exito"):
                            st.session_state.ultimo_pedido_id = t["result"]["resultado"].get("pedido_id")

                # Dibujar la respuesta en tiempo real en la pantalla
                with st.chat_message("assistant"):
                    texto_final = st.write_stream(generador_respuesta)
                    
                    # Si ejecutó el historial mediante Tool Calling, inyectamos las tarjetas visuales nativas aquí
                    if tools_ejecutadas:
                        for t in tools_ejecutadas:
                            if t["tool_name"] == "consultar_historial_cliente" and t["result"].get("exito"):
                                render_tarjetas_historial(t["result"]["resultado"].get("pedidos", []))
                
                # Persistir la traza limpia en la memoria de la sesión
                st.session_state.historial.append({
                    "rol": "assistant",
                    "texto": sanitizar_respuesta(texto_final),
                    "tools_ejecutadas": tools_ejecutadas
                })

        # ── RENDERIZADO DE FLUJOS INTERNOS DE PYTHON ──
        if es_respuesta_estatica:
            with st.chat_message("assistant"):
                st.write(respuesta_texto)
            st.session_state.historial.append({
                "rol": "assistant",
                "texto": respuesta_texto,
                "tools_ejecutadas": tools_ejecutadas
            })