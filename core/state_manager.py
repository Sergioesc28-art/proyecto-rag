import streamlit as st
from enum import Enum, auto

class EstadoConversacion(Enum):
    NORMAL = auto()
    ESPERANDO_CONFIRMACION_CONTACTO = auto()
    ESPERANDO_TIPO_ENTREGA = auto()
    ESPERANDO_DIRECCION = auto()

def inicializar_estado():
    """Inicializa todas las variables de sesión necesarias."""
    # Perfil e Historial
    if "historial" not in st.session_state:
        st.session_state.historial = []
    if "cliente_telefono" not in st.session_state:
        st.session_state.cliente_telefono = None
    if "cliente_nombre" not in st.session_state:
        st.session_state.cliente_nombre = None
    if "contexto_cliente" not in st.session_state:
        st.session_state.contexto_cliente = None
    if "ultimo_pedido_id" not in st.session_state:
        st.session_state.ultimo_pedido_id = None
    if "prompt_personalizado" not in st.session_state:
        st.session_state.prompt_personalizado = ""

    # Máquina de estados principal
    if "estado_conversacion" not in st.session_state:
        st.session_state.estado_conversacion = EstadoConversacion.NORMAL

    # Memoria a corto plazo del pedido
    if "pedido_pendiente" not in st.session_state:
        st.session_state.pedido_pendiente = None
    if "numero_contacto_final" not in st.session_state:
        st.session_state.numero_contacto_final = None

def resetear_flujo_pedido():
    """Limpia la memoria a corto plazo tras completar o cancelar un pedido."""
    st.session_state.estado_conversacion = EstadoConversacion.NORMAL
    st.session_state.pedido_pendiente = None
    st.session_state.numero_contacto_final = None