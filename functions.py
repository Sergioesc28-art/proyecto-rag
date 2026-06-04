"""Funciones de negocio de Yoyo Burguer."""

from __future__ import annotations

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
)


def _normalizar_producto(producto: str) -> Dict[str, Any] | None:
    return obtener_producto_por_nombre(producto)


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

    if isinstance(items, list) and all(isinstance(item, str) for item in items):
        return [item.strip() for item in items if item and item.strip()]

    if isinstance(items, list):
        nombres: List[str] = []
        for item in items:
            if isinstance(item, dict):
                nombre = item.get("producto") or item.get("nombre") or item.get("producto_nombre")
                if nombre:
                    nombres.append(str(nombre).strip())
        return nombres

    return []


def crear_pedido(items: List[Any]) -> dict:
    items_normalizados = _normalizar_items(items)
    if not items_normalizados:
        return {"error": "La lista de items no puede estar vacía."}

    return crear_nuevo_pedido(items_normalizados)


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

    minutos = 5 + (pedidos_activos * 4)
    return {
        "minutos_espera": minutos,
        "pedidos_activos": pedidos_activos,
        "mensaje": f"Tiempo estimado: {minutos} minutos.",
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
