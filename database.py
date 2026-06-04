"""database.py - Gestión de BD SQLite para Yoyo Burguer.

Esquema relacional 3NF compatible con la app y las herramientas de function calling.
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Dict, List, Optional

DB_PATH = "yoyo_burguer_3nf.db"

MENU_SEED = [
    {
        "nombre": "Hamburguesa Sencilla",
        "precio_base": 33.0,
        "tipo": "hamburguesa",
        "ingredientes": ["pan artesanal", "1 carne de res", "mayonesa", "lechuga", "jamón", "queso cheddar", "tocino"],
    },
    {
        "nombre": "Hamburguesa Doble Carne",
        "precio_base": 38.0,
        "tipo": "hamburguesa",
        "ingredientes": ["pan artesanal", "2 carnes de res", "mayonesa", "lechuga", "doble jamón", "queso cheddar", "tocino"],
    },
    {
        "nombre": "Hamburguesa Hawaiana",
        "precio_base": 39.0,
        "tipo": "hamburguesa",
        "ingredientes": ["pan artesanal", "1 carne de res", "mayonesa", "lechuga", "jamón extra", "queso cheddar", "tocino", "piña"],
    },
    {
        "nombre": "Hamburguesa Especial",
        "precio_base": 47.0,
        "tipo": "hamburguesa",
        "ingredientes": ["pan artesanal", "1 carne de res", "mayonesa", "lechuga", "doble jamón", "queso cheddar", "doble tocino", "piña", "salchicha de pavo"],
    },
    {
        "nombre": "Hamburguesa Especial Doble Carne",
        "precio_base": 55.0,
        "tipo": "hamburguesa",
        "ingredientes": ["pan artesanal", "2 carnes de res", "mayonesa", "lechuga", "doble jamón", "queso cheddar", "doble tocino", "piña", "salchicha de pavo"],
    },
    {
        "nombre": "Natsu Burger",
        "precio_base": 65.0,
        "tipo": "hamburguesa",
        "ingredientes": ["pan artesanal", "3 carnes de res", "mayonesa", "lechuga", "3 jamones", "queso cheddar", "3 tocinos", "piña", "salchicha de pavo", "cebolla caramelizada", "champiñones"],
    },
    {
        "nombre": "Hot Dog Sencillo",
        "precio_base": 19.0,
        "tipo": "hot dog",
        "ingredientes": ["pan tradicional", "1 salchicha de pavo", "mayonesa", "tocino", "cebolla"],
    },
    {
        "nombre": "Hot Dog Hawaiano",
        "precio_base": 22.0,
        "tipo": "hot dog",
        "ingredientes": ["pan tradicional", "1 salchicha de pavo", "mayonesa", "tocino extra", "cebolla", "piña"],
    },
    {
        "nombre": "Hot Dog Especial",
        "precio_base": 25.0,
        "tipo": "hot dog",
        "ingredientes": ["pan tradicional", "1 salchicha de pavo", "mayonesa", "tocino extra", "cebolla", "jamón", "queso cheddar"],
    },
    {
        "nombre": "Hot Dog Especial con Doble Salchicha",
        "precio_base": 28.0,
        "tipo": "hot dog",
        "ingredientes": ["pan tradicional", "2 salchichas de pavo", "mayonesa", "tocino extra", "cebolla", "jamón", "queso cheddar"],
    },
    {
        "nombre": "Papas a la francesa",
        "precio_base": 50.0,
        "tipo": "complemento",
        "ingredientes": ["papas fritas"],
    },
    {
        "nombre": "Salchichas tipo pulpo",
        "precio_base": 30.0,
        "tipo": "complemento",
        "ingredientes": ["salchichas tipo pulpo"],
    },
]

INGREDIENTE_PRECIOS = {
    "pan artesanal": 0.0,
    "pan tradicional": 0.0,
    "1 carne de res": 0.0,
    "2 carnes de res": 0.0,
    "3 carnes de res": 0.0,
    "mayonesa": 0.0,
    "lechuga": 0.0,
    "jamón": 0.0,
    "queso cheddar": 0.0,
    "tocino": 0.0,
    "piña": 0.0,
    "salchicha de pavo": 0.0,
    "3 jamones": 0.0,
    "3 tocinos": 0.0,
    "cebolla": 0.0,
    "papas fritas": 0.0,
    "salchichas tipo pulpo": 0.0,
    "doble jamón": 4.0,
    "jamón extra": 3.0,
    "doble tocino": 4.0,
    "tocino extra": 3.0,
    "cebolla caramelizada": 4.0,
    "champiñones": 5.0,
}

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _normalizar_telefono(telefono: str) -> str:
    return "".join(ch for ch in str(telefono) if ch.isdigit())


def _obtener_o_crear_ingrediente(cursor: sqlite3.Cursor, nombre: str) -> int:
    cursor.execute("SELECT id FROM ingredientes WHERE LOWER(nombre) = LOWER(?)", (nombre.strip(),))
    fila = cursor.fetchone()
    if fila:
        return int(fila[0])

    cursor.execute(
        "INSERT INTO ingredientes (nombre, precio_extra, disponible) VALUES (?, ?, 1)",
        (nombre.strip(), float(INGREDIENTE_PRECIOS.get(nombre.strip(), 0.0))),
    )
    return int(cursor.lastrowid)


def _obtener_ingredientes_producto(cursor: sqlite3.Cursor, producto_id: int) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT i.id, i.nombre, i.precio_extra, i.disponible, pi.es_removible
        FROM ingredientes i
        INNER JOIN producto_ingredientes pi ON pi.ingrediente_id = i.id
        WHERE pi.producto_id = ?
        ORDER BY i.nombre
        """,
        (producto_id,),
    )
    return [dict(fila) for fila in cursor.fetchall()]


def init_database() -> None:
    """Crea el esquema 3NF y carga los datos iniciales."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            telefono TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            direccion TEXT,
            numero_contacto_llamada TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            precio_base REAL NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('hamburguesa', 'hot dog', 'complemento')),
            disponible INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ingredientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            precio_extra REAL DEFAULT 0.0,
            disponible INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS producto_ingredientes (
            producto_id INTEGER NOT NULL,
            ingrediente_id INTEGER NOT NULL,
            es_removible INTEGER DEFAULT 1,
            PRIMARY KEY (producto_id, ingrediente_id),
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
            FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id TEXT UNIQUE NOT NULL,
            cliente_telefono TEXT,
            tipo_entrega TEXT NOT NULL CHECK(tipo_entrega IN ('presencial', 'domicilio')),
            direccion_entrega TEXT,
            costo_envio REAL DEFAULT 0,
            metodo_pago TEXT CHECK(metodo_pago IN ('efectivo', 'transferencia')),
            pago_validado INTEGER DEFAULT 0,
            total_productos REAL NOT NULL,
            total_envio REAL DEFAULT 0,
            descuento REAL DEFAULT 0,
            total_final REAL NOT NULL,
            estado TEXT DEFAULT 'pendiente_validacion',
            hora_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_telefono) REFERENCES clientes(telefono)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pedido_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id TEXT NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER DEFAULT 1,
            precio_unitario_base REAL NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pedido_item_modificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_item_id INTEGER NOT NULL,
            ingrediente_id INTEGER NOT NULL,
            accion TEXT NOT NULL CHECK(accion IN ('extra', 'sin')),
            costo_aplicado REAL DEFAULT 0.0,
            FOREIGN KEY (pedido_item_id) REFERENCES pedido_items(id) ON DELETE CASCADE,
            FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garantias_clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_telefono TEXT NOT NULL,
            pedido_origen_id TEXT NOT NULL,
            motivo_incidencia TEXT,
            estado TEXT DEFAULT 'disponible' CHECK(estado IN ('disponible', 'canjeada')),
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_telefono) REFERENCES clientes(telefono) ON DELETE CASCADE,
            FOREIGN KEY (pedido_origen_id) REFERENCES pedidos(pedido_id) ON DELETE CASCADE
        )
        """
    )

    cursor.execute("SELECT COUNT(*) AS total FROM productos")
    if cursor.fetchone()["total"] == 0:
        for producto in MENU_SEED:
            cursor.execute(
                "INSERT INTO productos (nombre, precio_base, tipo, disponible) VALUES (?, ?, ?, 1)",
                (producto["nombre"], producto["precio_base"], producto["tipo"]),
            )
            producto_id = int(cursor.lastrowid)
            for ingrediente in producto["ingredientes"]:
                ingrediente_id = _obtener_o_crear_ingrediente(cursor, ingrediente)
                cursor.execute(
                    "INSERT INTO producto_ingredientes (producto_id, ingrediente_id, es_removible) VALUES (?, ?, 1)",
                    (producto_id, ingrediente_id),
                )

    conn.commit()
    conn.close()


def cargar_menu_inicial() -> None:
    """Compatibilidad con código antiguo: el menú se carga desde init_database()."""


def obtener_producto_por_nombre(nombre: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE LOWER(nombre) = LOWER(?) LIMIT 1", (nombre.strip(),))
    producto = cursor.fetchone()

    if not producto:
        conn.close()
        return None

    ingredientes = _obtener_ingredientes_producto(cursor, int(producto["id"]))
    conn.close()

    resultado = dict(producto)
    resultado["precio"] = resultado["precio_base"]
    resultado["ingredientes"] = [item["nombre"] for item in ingredientes]
    resultado["ingredientes_detalle"] = ingredientes
    resultado["disponible"] = bool(resultado["disponible"])
    return resultado


def obtener_todos_productos() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos ORDER BY tipo, nombre")
    productos = cursor.fetchall()

    resultado: List[Dict[str, Any]] = []
    for producto in productos:
        info = dict(producto)
        info["precio"] = info["precio_base"]
        info["disponible"] = bool(info["disponible"])
        info["ingredientes"] = [item["nombre"] for item in _obtener_ingredientes_producto(cursor, int(info["id"]))]
        resultado.append(info)

    conn.close()
    return resultado


def obtener_pedido(pedido_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE pedido_id = ? LIMIT 1", (pedido_id.strip().upper(),))
    pedido = cursor.fetchone()
    if not pedido:
        conn.close()
        return None

    cursor.execute(
        """
        SELECT pi.id, pi.producto_id, p.nombre AS producto_nombre, pi.cantidad, pi.precio_unitario_base
        FROM pedido_items pi
        INNER JOIN productos p ON p.id = pi.producto_id
        WHERE pi.pedido_id = ?
        ORDER BY pi.id
        """,
        (pedido_id.strip().upper(),),
    )
    items = [dict(fila) for fila in cursor.fetchall()]
    conn.close()

    resultado = dict(pedido)
    resultado["pago_validado"] = bool(resultado["pago_validado"])
    resultado["items"] = items
    return resultado


def crear_nuevo_pedido(items_lista: List[str]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if not items_lista:
            return {"error": "La lista de items no puede estar vacía."}

        total_productos = 0.0
        productos_validos: List[Dict[str, Any]] = []

        for item_nombre in items_lista:
            producto = obtener_producto_por_nombre(item_nombre)
            if not producto:
                return {"error": f"Producto '{item_nombre}' no encontrado"}
            if not producto["disponible"]:
                return {"error": f"Producto '{producto['nombre']}' no disponible"}

            total_productos += float(producto["precio_base"])
            productos_validos.append(producto)

        pedido_id = f"PED-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute(
            """
            INSERT INTO pedidos (
                pedido_id, cliente_telefono, tipo_entrega, direccion_entrega,
                costo_envio, metodo_pago, pago_validado,
                total_productos, total_envio, descuento, total_final, estado
            ) VALUES (?, NULL, 'presencial', NULL, 0, 'efectivo', 0, ?, 0, 0, ?, 'pendiente_validacion')
            """,
            (pedido_id, total_productos, total_productos),
        )

        for producto in productos_validos:
            cursor.execute(
                "INSERT INTO pedido_items (pedido_id, producto_id, cantidad, precio_unitario_base) VALUES (?, ?, 1, ?)",
                (pedido_id, producto["id"], float(producto["precio_base"])),
            )

        conn.commit()
        return {
            "exito": True,
            "pedido_id": pedido_id,
            "items": [producto["nombre"] for producto in productos_validos],
            "total": round(total_productos, 2),
            "total_final": round(total_productos, 2),
            "estado": "pendiente_validacion",
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"Error al crear pedido: {str(e)}"}
    finally:
        conn.close()


def actualizar_estado_pedido(pedido_id: str, nuevo_estado: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE pedidos SET estado = ? WHERE pedido_id = ?", (nuevo_estado, pedido_id.strip().upper()))
        if cursor.rowcount == 0:
            return {"error": f"Pedido {pedido_id} no encontrado"}

        conn.commit()
        return {"exito": True, "pedido_id": pedido_id.strip().upper(), "estado": nuevo_estado}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def registrar_cliente_bd(nombre: str, telefono: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        telefono_limpio = _normalizar_telefono(telefono)
        if len(telefono_limpio) != 10:
            return {"error": "El teléfono debe tener exactamente 10 dígitos"}

        cursor.execute("SELECT telefono FROM clientes WHERE telefono = ?", (telefono_limpio,))
        if cursor.fetchone():
            return {"error": f"Teléfono {telefono_limpio} ya está registrado"}

        cursor.execute(
            "INSERT INTO clientes (telefono, nombre, direccion, numero_contacto_llamada) VALUES (?, ?, NULL, ?)",
            (telefono_limpio, nombre.strip(), telefono_limpio),
        )
        conn.commit()

        return {"exito": True, "cliente_id": telefono_limpio, "nombre": nombre.strip(), "telefono": telefono_limpio}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def obtener_historial_cliente(telefono: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        telefono_limpio = _normalizar_telefono(telefono)
        cursor.execute("SELECT * FROM clientes WHERE telefono = ?", (telefono_limpio,))
        cliente = cursor.fetchone()
        if not cliente:
            return {"error": f"Cliente con teléfono {telefono_limpio} no encontrado"}

        cursor.execute(
            """
            SELECT pedido_id, tipo_entrega, metodo_pago, total_productos, total_envio,
                   descuento, total_final, estado, hora_creacion
            FROM pedidos
            WHERE cliente_telefono = ?
            ORDER BY hora_creacion DESC
            """,
            (telefono_limpio,),
        )
        pedidos = [dict(fila) for fila in cursor.fetchall()]

        return {
            "cliente_id": cliente["telefono"],
            "nombre": cliente["nombre"],
            "telefono": cliente["telefono"],
            "total_pedidos": len(pedidos),
            "pedidos": pedidos,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


# Inicializar la BD cuando se importa el módulo.
init_database()
