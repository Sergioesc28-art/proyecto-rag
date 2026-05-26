# functions.py — Funciones reales de Yoyo's Burguer con BD SQLite
# La IA llama estas funciones para obtener datos de la BD
# Tu app.py es quien llama estas funciones cuando la IA lo pide.

import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Importar funciones de la BD
from database import (
    obtener_producto_por_nombre,
    obtener_todos_productos,
    obtener_pedido,
    crear_nuevo_pedido,
    actualizar_estado_pedido,
    aplicar_descuento_a_pedido,
    registrar_cliente_bd,
    obtener_historial_cliente,
    get_connection
)


# ── 1. Consultar menú completo ──────────────────────────────────
def consultar_menu() -> dict:
    """
    Devuelve el menú completo de Yoyo Burguer con precios y disponibilidad.

    Returns:
        dict con nombre del producto, precio, tipo y disponibilidad.
    """
    productos = obtener_todos_productos()
    
    resultado = {
        "hamburguesas": [],
        "hot_dogs": [],
        "complementos": [],
        "total": len(productos)
    }
    
    for p in productos:
        item = {
            "nombre": p["nombre"],
            "precio": p["precio"],
            "disponible": p["disponible"],
            "tipo": p["tipo"]
        }
        
        if p["tipo"] == "hamburguesa":
            resultado["hamburguesas"].append(item)
        elif p["tipo"] == "hot dog":
            resultado["hot_dogs"].append(item)
        elif p["tipo"] == "complemento":
            resultado["complementos"].append(item)
    
    return resultado


# ── 2. Verificar disponibilidad ─────────────────────────────────
def verificar_disponibilidad(producto: str) -> dict:
    """
    Verifica si un producto específico está disponible para ordenar.

    Args:
        producto: Nombre del producto (ej: 'Hamburguesa Sencilla').

    Returns:
        dict con 'disponible', precio y mensaje explicativo.
    """
    p = obtener_producto_por_nombre(producto)
    
    if not p:
        return {
            "disponible": False,
            "mensaje": f"'{producto}' no existe en el menú."
        }
    
    return {
        "disponible": p["disponible"],
        "nombre_producto": p["nombre"],
        "precio": p["precio"],
        "tipo": p["tipo"],
        "mensaje": f"'{p['nombre']}' {'está disponible.' if p['disponible'] else 'no está disponible en este momento.'}"
    }


# ── 3. Consultar ingredientes ───────────────────────────────────
def consultar_ingredientes(producto: str) -> dict:
    """
    Devuelve la lista de ingredientes de un producto específico.

    Args:
        producto: Nombre del producto (ej: 'Hamburguesa Sencilla').

    Returns:
        dict con ingredientes, precio, tipo y disponibilidad.
    """
    p = obtener_producto_por_nombre(producto)
    
    if not p:
        return {"error": f"'{producto}' no está en el menú."}
    
    return {
        "nombre": p["nombre"],
        "tipo": p["tipo"],
        "precio": p["precio"],
        "disponible": p["disponible"],
        "ingredientes": p["ingredientes"]
    }


# ── 4. Crear pedido ─────────────────────────────────────────────
def crear_pedido(items: List[str]) -> dict:
    """
    Registra un nuevo pedido con los productos indicados.

    Args:
        items: Lista de nombres de productos (ej: ['Hamburguesa Sencilla', 'Papas a la francesa']).

    Returns:
        dict con pedido_id, total, desglose y estado.
    """
    if not items or len(items) == 0:
        return {"error": "La lista de items no puede estar vacía."}
    
    resultado = crear_nuevo_pedido(items)
    return resultado


# ── 5. Consultar estado de pedido ───────────────────────────────
def consultar_estado_pedido(pedido_id: str) -> dict:
    """
    Revisa el estado actual de un pedido existente.

    Args:
        pedido_id: ID del pedido (ej: 'PED-1001').

    Returns:
        dict con estado actual, items, total y hora.
    """
    pedido_id = pedido_id.strip().upper()
    pedido = obtener_pedido(pedido_id)
    
    if not pedido:
        return {"error": f"No se encontró el pedido '{pedido_id}'."}
    
    return {
        "pedido_id": pedido_id,
        "estado": pedido["estado"],
        "total": pedido["total"],
        "descuento": pedido["descuento"],
        "total_final": pedido["total_final"],
        "hora_creacion": pedido["hora_creacion"]
    }


# ── 6. Cancelar pedido ──────────────────────────────────────────
def cancelar_pedido(pedido_id: str) -> dict:
    """
    Cancela un pedido activo que aún no ha sido entregado.

    Args:
        pedido_id: ID del pedido a cancelar (ej: 'PED-1001').

    Returns:
        dict con confirmación o error si ya fue entregado.
    """
    pedido_id = pedido_id.strip().upper()
    
    resultado = actualizar_estado_pedido(pedido_id, "cancelado")
    
    if "error" in resultado:
        return resultado
    
    return {
        "exito": True,
        "pedido_id": pedido_id,
        "estado": "cancelado",
        "mensaje": f"Pedido {pedido_id} cancelado correctamente."
    }


# ── 7. Aplicar descuento ────────────────────────────────────────
def aplicar_descuento(pedido_id: str, codigo: str) -> dict:
    """
    Valida un código de descuento y lo aplica a un pedido existente.

    Args:
        pedido_id: ID del pedido (ej: 'PED-1001').
        codigo: Código promocional (ej: 'YOYO10').

    Returns:
        dict con nuevo total y porcentaje de descuento aplicado.
    """
    pedido_id = pedido_id.strip().upper()
    
    resultado = aplicar_descuento_a_pedido(pedido_id, codigo)
    
    if "error" in resultado:
        return resultado
    
    return {
        "exito": True,
        "pedido_id": pedido_id,
        "descuento_aplicado": f"{resultado['porcentaje']}%",
        "ahorro": resultado["descuento"],
        "total_anterior": resultado["total_anterior"],
        "total_final": resultado["total_final"],
        "mensaje": f"Descuento aplicado. Nuevo total: ${resultado['total_final']} MXN."
    }


# ── 8. Consultar tiempo de espera ───────────────────────────────
def consultar_tiempo_espera() -> dict:
    """
    Devuelve el tiempo estimado de espera basado en pedidos activos.

    Returns:
        dict con minutos_espera y pedidos_activos.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE estado = 'en_cocina'")
    pedidos_activos = cursor.fetchone()[0]
    conn.close()
    
    # Lógica: 5 minutos base + 4 minutos por pedido
    minutos = 5 + (pedidos_activos * 4)
    
    return {
        "minutos_espera": minutos,
        "pedidos_activos": pedidos_activos,
        "mensaje": f"Tiempo estimado: {minutos} minutos."
    }


# ── 9. Registrar cliente ────────────────────────────────────────
def registrar_cliente(nombre: str, telefono: str) -> dict:
    """
    Registra un nuevo cliente en el sistema.

    Args:
        nombre: Nombre completo del cliente.
        telefono: Número de teléfono a 10 dígitos.

    Returns:
        dict con confirmación, cliente_id o error.
    """
    resultado = registrar_cliente_bd(nombre, telefono)
    
    if "error" in resultado:
        return resultado
    
    return {
        "exito": True,
        "cliente_id": resultado["cliente_id"],
        "nombre": resultado["nombre"],
        "telefono": resultado["telefono"],
        "mensaje": f"Cliente '{nombre}' registrado exitosamente con ID {resultado['cliente_id']}."
    }


# ── 10. Consultar historial de cliente ──────────────────────────
def consultar_historial_cliente(telefono: str) -> dict:
    """
    Devuelve el historial de pedidos anteriores de un cliente.

    Args:
        telefono: Número de teléfono del cliente (10 dígitos).

    Returns:
        dict con nombre, ID del cliente y lista de pedidos.
    """
    resultado = obtener_historial_cliente(telefono)
    
    if "error" in resultado:
        return resultado
    
    return {
        "cliente_id": resultado["cliente_id"],
        "nombre": resultado["nombre"],
        "telefono": resultado["telefono"],
        "total_pedidos": resultado["total_pedidos"],
        "pedidos": resultado["pedidos"]
    }


# ── 11. Obtener información de Yoyo Burguer ────────────────────
def obtener_informacion_yoyo() -> dict:
    """
    Devuelve información general del establecimiento Yoyo Burguer.

    Returns:
        dict con horarios, ubicación, políticas, etc.
    """
    return {
        "nombre": "Yoyo Burguer",
        "ubicacion": "Calle 20 #99, por 21 y 21-A, fraccionamiento Los Arcos, C.P. 97390, Umán, Yucatán",
        "telefono": "999 325 8671",
        "horario": {
            "dias_apertura": "Viernes a Lunes",
            "hora_apertura": "6:00 PM",
            "hora_cierre": "11:00 PM",
            "ultima_orden_domicilio": "10:00 PM",
            "dias_cierre": "Martes, Miércoles, Jueves"
        },
        "servicios": {
            "consumo_en_local": "Disponible (15-20 minutos de preparación)",
            "entrega_domicilio": "Disponible en Umán (30-40 minutos)",
            "zona_cobertura": "Municipio de Umán",
            "pedido_minimo": "$100.00 MXN",
            "costo_envio": "$10.00 - $15.00 MXN (tarifa dinámica)"
        },
        "metodos_pago": ["Efectivo", "Transferencia bancaria (5250 3451 5369 3415)"],
        "politicas": {
            "personalizacion": "Permite retiro de ingredientes sin costo",
            "ingredientes_extra": "$3.00 - $5.00 MXN por ingrediente",
            "bebidas": "No se venden (pueden traer propias)",
            "promociones": "No disponibles actualmente",
            "combos": "No disponibles"
        }
    }


# ── 12. Obtener complementos ────────────────────────────────────
def obtener_complementos() -> dict:
    """
    Devuelve todos los complementos y guarniciones disponibles.

    Returns:
        dict con complementos, precios y información de extras.
    """
    productos = obtener_todos_productos()
    complementos = [p for p in productos if p["tipo"] == "complemento"]
    
    return {
        "complementos": complementos,
        "cantidad": len(complementos),
        "extras_independientes": {
            "costo_por_ingrediente": "$3.00 - $5.00 MXN",
            "aplicable_a": ["Hamburguesas", "Hot Dogs"]
        }
    }
