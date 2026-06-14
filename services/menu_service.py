import streamlit as st
from typing import Any, Dict
from infrastructure.database import obtener_producto_por_nombre, obtener_todos_productos

def _normalizar_producto(producto: str) -> Dict[str, Any] | None:
    return obtener_producto_por_nombre(producto)

@st.cache_data(ttl=60)
def consultar_menu() -> dict:
    """Obtiene el menú organizado por categorías. Cacheado por 60 segundos."""
    productos = obtener_todos_productos()
    resultado = {
        "hamburguesas": [],
        "hot_dogs": [],
        "complementos": [],
        "total": len(productos),
    }

    for producto in productos:
        item = {
            "id": producto["id"],
            "nombre": producto["nombre"],
            "precio_base": producto["precio_base"],
            "precio": producto["precio_base"],
            "tipo": producto["tipo"],
            "disponible": producto["disponible"],
        }
        if producto["tipo"] == "hamburguesa":
            resultado["hamburguesas"].append(item)
        elif producto["tipo"] == "hot dog":
            resultado["hot_dogs"].append(item)
        elif producto["tipo"] == "complemento":
            resultado["complementos"].append(item)

    return resultado

def verificar_disponibilidad(producto: str) -> dict:
    p = _normalizar_producto(producto)
    if not p:
        return {"disponible": False, "mensaje": f"'{producto}' no existe en el menú."}
    return {
        "disponible": bool(p["disponible"]),
        "producto_id": p["id"],
        "nombre_producto": p["nombre"],
        "precio_base": p["precio_base"],
        "precio": p["precio_base"],
        "tipo": p["tipo"],
        "mensaje": f"'{p['nombre']}' {'está disponible.' if p['disponible'] else 'no está disponible en este momento.'}",
    }

def consultar_ingredientes(producto: str) -> dict:
    p = _normalizar_producto(producto)
    if not p:
        return {"error": f"'{producto}' no está en el menú."}
    return {
        "nombre": p["nombre"],
        "producto": p["nombre"],
        "tipo": p["tipo"],
        "precio_base": p["precio_base"],
        "precio": p["precio_base"],
        "disponible": bool(p["disponible"]),
        "ingredientes": p["ingredientes"],
        "ingredientes_detalle": p.get("ingredientes_detalle", []),
    }

def obtener_complementos() -> dict:
    productos = obtener_todos_productos()
    complementos = [
        {
            "id": p["id"],
            "nombre": p["nombre"],
            "precio_base": p["precio_base"],
            "precio": p["precio_base"],
            "disponible": p["disponible"],
        }
        for p in productos if p["tipo"] == "complemento"
    ]
    return {
        "complementos": complementos,
        "porciones": "Papas a la francesa (3-4 personas), Salchichas tipo pulpo (2-3 personas)",
    }

def obtener_informacion_yoyo() -> dict:
    return {
        "nombre": "Yoyo Burguer",
        "ubicacion": "Calle 20 #99, por 21 y 21-A, fraccionamiento Los Arcos, C.P. 97390, Umán, Yucatán",
        "telefono": "999 325 8671",
        "horario": {
            "dias_apertura": "Viernes a Lunes",
            "hora_apertura": "6:00 PM",
            "hora_cierre": "11:00 PM",
            "ultima_orden_domicilio": "10:00 PM",
            "dias_cierre": "Martes, Miércoles, Jueves",
        },
        "servicios": {
            "consumo_en_local": "Disponible (15-20 minutos de preparación)",
            "entrega_domicilio": "Disponible en Umán (30-40 minutos)",
            "zona_cobertura": "Municipio de Umán",
            "pedido_minimo": "$100.00 MXN",
            "costo_envio": "$10.00 - $15.00 MXN (tarifa dinámica)",
        },
        "metodos_pago": ["Efectivo", "Transferencia bancaria (5250 3451 5369 3415)"],
        "politicas": {
            "personalizacion": "Permite retiro de ingredientes sin costo",
            "ingredientes_extra": "$3.00 - $5.00 MXN por ingrediente",
            "bebidas": "No se venden (pueden traer propias)",
            "promociones": "No disponibles actualmente",
            "combos": "No disponibles",
        },
    }