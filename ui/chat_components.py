import streamlit as st

def render_header():
    """Muestra el título y los avisos principales de la aplicación."""
    st.title("Yoyo's IA 🍔")
    st.info(
        "Ingresa tu número de cuenta en el panel lateral para comenzar. "
        "Si ya validaste un número de contacto para tu pedido actual, no te lo volveré a pedir."
    )

def render_chat_history():
    """Recorre y renderiza todos los mensajes guardados en el historial."""
    # Seguridad: Si por alguna razón no existe el historial, lo creamos vacío
    if "historial" not in st.session_state:
        st.session_state.historial = []

    for mensaje in st.session_state.historial:
        with st.chat_message(mensaje["rol"]):
            st.write(mensaje["texto"])

def display_user_message(texto: str):
    """
    Dibuja el mensaje del usuario en pantalla y lo inyecta en el historial de sesión.
    """
    with st.chat_message("user"):
        st.write(texto)

    st.session_state.historial.append({
        "rol": "user",
        "texto": texto,
        "tools_ejecutadas": None
    })

def display_assistant_message(texto_limpio: str, tools_ejecutadas: list = None):
    """
    Dibuja la respuesta final del LLM en pantalla y guarda la traza en el historial.
    """
    with st.chat_message("assistant"):
        st.write(texto_limpio)

    st.session_state.historial.append({
        "rol": "assistant",
        "texto": texto_limpio,
        "tools_ejecutadas": tools_ejecutadas
    })

def render_loading_spinner(mensaje="Procesando..."):
    """
    Retorna el contexto del spinner. Útil para envolver llamadas al LLM.
    Uso: with render_loading_spinner():
    """
    return st.spinner(mensaje)