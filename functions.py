"""Funciones de negocio de Yoyo Burguer."""

from __future__ import annotations
import streamlit as st

import re
from typing import Any, Dict, List

from database import (
    crear_nuevo_pedido,
    get_connection,
    obtener_historial_cliente,
    obtener_pedido,
    obtener_producto_por_nombre,
    obtener_todos_productos,
    registrar_cliente_bd,
    actualizar_estado_pedido,
    actualizar_direccion_cliente,
)


def _normalizar_producto(producto: str) -> Dict[str, Any] | None:
    return obtener_producto_por_nombre(producto)


# FIX 3: el menú no cambia entre requests. Con ttl=60 se refresca
# cada minuto automáticamente, pero mientras tanto no toca SQLite.
@st.cache_data(ttl=60)
def consultar_menu() -> dict:
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


def _normalizar_items(items: Any) -> List[str]:
    if not items:
        return []

    if isinstance(items, str):
        partes = re.split(r"(?:\s*,\s*|\s+y\s+|\s+e\s+|\n)+", items, flags=re.IGNORECASE)
        return [parte.strip(" .;:-") for parte in partes if parte and parte.strip(" .;:-")]

    if isinstance(items, dict):
        if "items" in items:
            return _normalizar_items(items.get("items"))
        nombre = items.get("producto") or items.get("nombre") or items.get("producto_nombre")
        if nombre:
            return [str(nombre).strip()]
        return []

    if isinstance(items, list) and all(isinstance(item, str) for item in items):
        return [item.strip(" .;:-") for item in items if item and item.strip(" .;:-")]

    if isinstance(items, list):
        nombres: List[str] = []
        for item in items:
            if isinstance(item, str):
                nombres.extend(_normalizar_items(item))
                continue
            if isinstance(item, dict):
                if "items" in item:
                    nombres.extend(_normalizar_items(item.get("items")))
                    continue
                nombre = item.get("producto") or item.get("nombre") or item.get("producto_nombre")
                if nombre:
                    nombres.append(str(nombre).strip())

        normalizados: List[str] = []
        vistos = set()
        for nombre in nombres:
            nombre_limpio = re.sub(r"\s+", " ", str(nombre)).strip(" .;:-")
            clave = nombre_limpio.lower()
            if nombre_limpio and clave not in vistos:
                vistos.add(clave)
                normalizados.append(nombre_limpio)

        return normalizados

    return []


def crear_pedido(
    items: Any,
    telefono: str | None = None,
    nombre: str | None = None,
    tipo_entrega: str = "presencial",
    direccion: str | None = None,
) -> dict:
    items_normalizados = _normalizar_items(items)
    if not items_normalizados:
        return {"error": "La lista de items no puede estar vacía."}
    return crear_nuevo_pedido(
        items_normalizados,
        cliente_telefono=telefono,
        cliente_nombre=nombre,
        tipo_entrega=tipo_entrega,
        direccion=direccion,
    )


def guardar_direccion_cliente(telefono: str, direccion: str) -> dict:
    """Guarda la dirección del cliente en Supabase."""
    return actualizar_direccion_cliente(telefono, direccion)


def consultar_estado_pedido(pedido_id: str) -> dict:
    pedido = obtener_pedido(pedido_id)
    if not pedido:
        return {"error": f"No se encontró el pedido '{pedido_id}'."}

    return {
        "pedido_id": pedido["pedido_id"],
        "estado": pedido["estado"],
        "pago_validado": bool(pedido["pago_validado"]),
        "tipo_entrega": pedido["tipo_entrega"],
        "total_productos": pedido["total_productos"],
        "total_envio": pedido["total_envio"],
        "descuento": pedido["descuento"],
        "total_final": pedido["total_final"],
        "hora_creacion": pedido["hora_creacion"],
        "items": pedido.get("items", []),
    }


def cancelar_pedido(pedido_id: str) -> dict:
    pedido = obtener_pedido(pedido_id)
    if not pedido:
        return {"error": "Pedido no encontrado."}
    if pedido["estado"] in ["entregado", "en_ruta"]:
        return {"error": "El pedido ya fue preparado/enviado y no puede cancelarse."}
    return actualizar_estado_pedido(pedido_id, "cancelado")


def consultar_tiempo_espera() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE estado IN ('pendiente_validacion', 'en_cocina')")
    pedidos_activos = cursor.fetchone()["total"]
    conn.close()

    tiempo_base = 5
    minutos_por_pedido = 4
    minutos = tiempo_base + (pedidos_activos * minutos_por_pedido)
    return {
        "minutos_espera": minutos,
        "pedidos_activos": pedidos_activos,
        "tiempo_base": tiempo_base,
        "minutos_por_pedido": minutos_por_pedido,
        "mensaje": f"Tiempo estimado: {minutos} minutos. Cálculo: {tiempo_base} minutos base + {minutos_por_pedido} minutos por pedido activo.",
    }


def registrar_cliente(nombre: str, telefono: str) -> dict:
    resultado = registrar_cliente_bd(nombre, telefono)
    if "error" in resultado:
        return resultado
    return {
        "exito": True,
        "cliente_id": resultado["cliente_id"],
        "nombre": resultado["nombre"],
        "telefono": resultado["telefono"],
        "mensaje": f"Cliente '{nombre}' registrado exitosamente con ID {resultado['cliente_id']}.",
    }


def consultar_historial_cliente(telefono: str) -> dict:
    resultado = obtener_historial_cliente(telefono)
    if "error" in resultado:
        return resultado
    return {
        "cliente_id": resultado["cliente_id"],
        "nombre": resultado["nombre"],
        "telefono": resultado["telefono"],
        "total_pedidos": resultado["total_pedidos"],
        "pedidos": resultado["pedidos"],
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


def obtener_complementos() -> dict:
    productos = obtener_todos_productos()
    complementos = [
        {
            "id": producto["id"],
            "nombre": producto["nombre"],
            "precio_base": producto["precio_base"],
            "precio": producto["precio_base"],
            "disponible": producto["disponible"],
        }
        for producto in productos
        if producto["tipo"] == "complemento"
    ]
    return {
        "complementos": complementos,
        "porciones": "Papas a la francesa (3-4 personas), Salchichas tipo pulpo (2-3 personas)",
    }


def validar_pago_pedido(pedido_id: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE pedidos SET pago_validado = 1, estado = 'en_cocina' WHERE pedido_id = ?",
        (pedido_id.strip().upper(),),
    )
    if cursor.rowcount == 0:
        conn.close()
        return {"error": "Pedido no encontrado."}
    conn.commit()
    conn.close()
    return {"exito": True, "mensaje": f"Pago validado para el pedido {pedido_id}."}


def obtener_contexto_cliente(telefono: str) -> str:
    """
    Arma un string de contexto personalizado del cliente para inyectar
    en el system prompt. Se llama una sola vez cuando el cliente da su
    teléfono y se guarda en st.session_state.contexto_cliente.
    """
    from collections import Counter

    resultado = obtener_historial_cliente(telefono)

    if "error" in resultado:
        return f"Cliente nuevo (teléfono: {telefono}). Sin historial previo."

    nombre    = resultado.get("nombre", "Cliente")
    direccion = resultado.get("direccion") or "No registrada"
    total     = resultado.get("total_pedidos", 0)
    pedidos   = resultado.get("pedidos", [])

    # Últimos 4 pedidos
    ultimos = pedidos[:4]
    lineas_pedidos = [
        f"  - {p['pedido_id']}: ${p['total_final']} MXN | estado: {p['estado']}"
        for p in ultimos
    ] or ["  - Sin pedidos previos"]

    # Productos favoritos (top 3 más pedidos)
    conteo: Counter = Counter()
    for p in pedidos:
        for item in p.get("items", []):
            nombre_item = item.get("producto_nombre", "")
            if nombre_item:
                conteo[nombre_item] += item.get("cantidad", 1)

    favoritos = (
        ", ".join(f"{prod} (x{cnt})" for prod, cnt in conteo.most_common(3))
        if conteo else "Sin datos suficientes"
    )

    return (
        f"=== CONTEXTO DEL CLIENTE ===\n"
        f"Nombre: {nombre}\n"
        f"Teléfono: {telefono}\n"
        f"Dirección: {direccion}\n"
        f"Total de pedidos históricos: {total}\n"
        f"Últimos 4 pedidos:\n" + "\n".join(lineas_pedidos) + "\n"
        f"Productos favoritos: {favoritos}\n"
        f"==========================="
    )