import streamlit as st

def render_header():
    """Muestra el título y los avisos principales de la aplicación."""
    st.title("Yoyo's IA 🍔")
    st.info(
        "Ingresa tu número de cuenta en el panel lateral para comenzar. "
        "Si ya validaste un número de contacto para tu pedido actual, no te lo volveré a pedir."
    )

def render_tarjetas_historial(pedidos):
    """Dibuja el historial de pedidos usando componentes nativos de Streamlit."""
    if not pedidos:
        st.info("Aún no tienes pedidos registrados en tu historial.")
        return
        
    # Mostrar máximo los últimos 3 pedidos para no saturar la pantalla
    for i, pedido in enumerate(pedidos[:3]): 
        items_str = ", ".join([f"{item.get('cantidad', 1)}x {item.get('producto_nombre', 'Producto')}" for item in pedido.get('items', [])])
        estado = pedido.get('estado', '').replace('_', ' ').title()
        tipo = pedido.get('tipo_entrega', '').title()
        total = float(pedido.get('total_final', 0.0))

        # Tarjeta visual nativa de Streamlit
        with st.container(border=True):
            st.markdown(f"**🍔 Pedido {i+1}** | Estado: `{estado}`")
            st.write(f"**Total:** ${total:.2f} MXN • **Entrega:** {tipo}")
            st.caption(f"🛒 *{items_str}*")

def render_chat_history():
    """Recorre y renderiza todos los mensajes guardados en el historial."""
    # Seguridad: Si por alguna razón no existe el historial, lo creamos vacío
    if "historial" not in st.session_state:
        st.session_state.historial = []

    for mensaje in st.session_state.historial:
        with st.chat_message(mensaje["rol"]):
            st.write(mensaje["texto"])
            
            # Si la IA ejecutó el historial, dibujamos las tarjetas al recargar la página
            if mensaje.get("tools_ejecutadas"):
                for t in mensaje["tools_ejecutadas"]:
                    if t["tool_name"] == "consultar_historial_cliente" and t["result"].get("exito"):
                        render_tarjetas_historial(t["result"]["resultado"].get("pedidos", []))

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