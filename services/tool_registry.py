"""tool_registry.py - Registro central de herramientas para el LLM."""

import traceback
from services.menu_service import (
    consultar_menu, verificar_disponibilidad, consultar_ingredientes,
    obtener_complementos, obtener_informacion_yoyo
)
from services.order_service import (
    crear_pedido, consultar_estado_pedido, cancelar_pedido,
    consultar_tiempo_espera, validar_pago_pedido
)
from services.customer_service import (
    registrar_cliente, consultar_historial_cliente
)

# Diccionario central de herramientas disponibles
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

def ejecutar_herramienta(nombre_funcion: str, argumentos: dict) -> dict:
    """Ejecuta de manera segura cualquier función solicitada por Ollama."""
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