import streamlit as st
import re

def render_sidebar(fetch_context_callback=None):
    with st.sidebar:
        st.header("👤 Perfil del Cliente")
        telefono_sidebar = st.text_input(
            "Número de cuenta (10 dígitos):", 
            max_chars=10, 
            help="Tu identificador principal para historial y pedidos."
        )
        nombre_sidebar = st.text_input("Tu Nombre (Opcional):", placeholder="Ej: Natsu")
        
    # Sincronización de estado
    if nombre_sidebar:
        st.session_state.cliente_nombre = nombre_sidebar.strip()

    telefono_activo = re.sub(r"\D", "", telefono_sidebar) if telefono_sidebar else None

    if telefono_activo and len(telefono_activo) == 10:
        if st.session_state.get("cliente_telefono") != telefono_activo:
            st.session_state.cliente_telefono = telefono_activo
            if fetch_context_callback:
                st.session_state.contexto_cliente = fetch_context_callback(telefono_activo)
            
            st.session_state.contacto_confirmado = False
            st.session_state.numero_contacto_final = None
    else:
        st.session_state.cliente_telefono = None