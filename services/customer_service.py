from collections import Counter
from infrastructure.database import (
    registrar_cliente_bd,
    obtener_historial_cliente,
    actualizar_direccion_cliente
)

def registrar_cliente(nombre: str, telefono: str) -> dict:
    resultado = registrar_cliente_bd(nombre, telefono)
    if "error" in resultado:
        return resultado
    return {
        "exito": True,
        "cliente_id": resultado["cliente_id"],
        "nombre": resultado["nombre"],
        "telefono": resultado["telefono"],
        "mensaje": f"Cliente '{nombre}' registrado exitosamente.",
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

def guardar_direccion_cliente(telefono: str, direccion: str) -> dict:
    return actualizar_direccion_cliente(telefono, direccion)

def obtener_contexto_cliente(telefono: str) -> str:
    """Arma un string de contexto personalizado para inyectar en el LLM."""
    resultado = obtener_historial_cliente(telefono)
    if "error" in resultado:
        return f"Cliente nuevo (teléfono de cuenta: {telefono}). Sin historial previo."

    nombre    = resultado.get("nombre", "Cliente")
    direccion = resultado.get("direccion") or "No registrada"
    total     = resultado.get("total_pedidos", 0)
    pedidos   = resultado.get("pedidos", [])
    numero_contacto = resultado.get("numero_contacto", telefono)

    # Solo extraemos los favoritos, omitimos inyectar los IDs de pedidos para evitar alucinaciones
    conteo = Counter()
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
        f"[Inicio del Contexto del Cliente]\n"
        f"Nombre: {nombre}\n"
        f"Teléfono de Cuenta: {telefono}\n"
        f"Número de Contacto Principal: {numero_contacto}\n"
        f"Dirección: {direccion}\n"
        f"Total de pedidos históricos: {total}\n"
        f"Productos favoritos: {favoritos}\n"
        f"[Fin del Contexto del Cliente]"
    )