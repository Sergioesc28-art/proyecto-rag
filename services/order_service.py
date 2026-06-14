import re
from typing import Any, List
from infrastructure.database import (
    crear_nuevo_pedido,
    obtener_pedido,
    actualizar_estado_pedido,
    get_connection
)

def _normalizar_items(items: Any) -> List[str]:
    """Extrae y limpia los nombres de productos desde distintos formatos de entrada."""
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

    if isinstance(items, list):
        nombres: List[str] = []
        for item in items:
            if isinstance(item, str):
                nombres.extend(_normalizar_items(item))
            elif isinstance(item, dict):
                if "items" in item:
                    nombres.extend(_normalizar_items(item.get("items")))
                else:
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
    numero_contacto: str | None = None,
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
        numero_contacto=numero_contacto,
    )

def consultar_estado_pedido(pedido_id: str) -> dict:
    pedido = obtener_pedido(pedido_id)
    if not pedido:
        return {"error": f"No se encontró el pedido '{pedido_id}'."}
    return {
        "pedido_id": pedido["pedido_id"],
        "estado": pedido["estado"],
        "pago_validado": bool(pedido["pago_validado"]),
        "tipo_entrega": pedido["tipo_entrega"],
        "total_productos": float(pedido["total_productos"]),
        "total_envio": float(pedido["total_envio"]),
        "total_final": float(pedido["total_final"]),
        "hora_creacion": pedido["hora_creacion"],
        "items": pedido.get("items", []),
    }

def cancelar_pedido(pedido_id: str) -> dict:
    pedido = obtener_pedido(pedido_id)
    if not pedido:
        return {"error": "Pedido no encontrado."}
    if pedido["estado"] in ["entregado", "en_ruta", "listo"]:
        return {"error": "El pedido ya fue preparado/enviado y no puede cancelarse."}
    return actualizar_estado_pedido(pedido_id, "cancelado")

def consultar_tiempo_espera() -> dict:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE estado IN ('pendiente_validacion', 'en_cocina')")
        pedidos_activos = cursor.fetchone()["total"]
    finally:
        from infrastructure.database import release_connection
        release_connection(conn)

    tiempo_base = 5
    minutos_por_pedido = 4
    minutos = tiempo_base + (pedidos_activos * minutos_por_pedido)
    return {
        "minutos_espera": minutos,
        "pedidos_activos": pedidos_activos,
        "tiempo_base": tiempo_base,
        "minutos_por_pedido": minutos_por_pedido,
        "mensaje": f"Tiempo estimado: {minutos} minutos. Cálculo: {tiempo_base} min base + {minutos_por_pedido} min por pedido activo.",
    }

def validar_pago_pedido(pedido_id: str) -> dict:
    return actualizar_estado_pedido(pedido_id, "en_cocina") # Asumiendo que la BD actualiza la flag 'pago_validado' vía un trigger o lo añades a `actualizar_estado_pedido`.