import streamlit as st
import re

def render_sidebar(fetch_context_callback=None):
    """
    Renderiza el panel lateral y maneja el estado visual de los inputs.
    
    Args:
        fetch_context_callback (callable): Función para obtener el contexto 
                                           del cliente si el teléfono cambia.
    """
    with st.sidebar:
        st.header("👤 Perfil del Cliente")
        telefono_sidebar = st.text_input(
            "Número de cuenta (10 dígitos):", 
            max_chars=10, 
            help="Tu identificador principal para historial y pedidos."
        )

        nombre_sidebar = st.text_input("Tu Nombre (Opcional):", placeholder="Ej: Natsu")
        
        st.header("⚙️ Configuración del Asistente")
        prompt_personalizado = st.text_area(
            "Instrucciones dinámicas para la IA:",
            value="",
            placeholder="Ej: Hoy hay promoción de papas gratis. Sé muy entusiasta."
        )

    # ── Sincronización con el Estado Global (Session State) ──
    if nombre_sidebar:
        st.session_state.cliente_nombre = nombre_sidebar.strip()

    # Limpiamos el input para dejar solo dígitos
    telefono_activo = re.sub(r"\D", "", telefono_sidebar) if telefono_sidebar else None

    if telefono_activo and len(telefono_activo) == 10:
        # Si el número cambia, actualizamos y disparamos el callback
        if st.session_state.get("cliente_telefono") != telefono_activo:
            st.session_state.cliente_telefono = telefono_activo
            
            # Delegamos la lógica de base de datos hacia el servicio inyectado
            if fetch_context_callback:
                st.session_state.contexto_cliente = fetch_context_callback(telefono_activo)
            
            # Reseteamos flujos de confirmación por ser cliente nuevo
            st.session_state.contacto_confirmado = False
            st.session_state.numero_contacto_final = None
    else:
        st.session_state.cliente_telefono = None

    # Guardamos la instrucción extra para el LLM
    st.session_state.prompt_personalizado = prompt_personalizado