"""database.py - Gestión de BD PostgreSQL (Supabase) para Yoyo Burguer.
Maneja connection pooling y consultas SQL crudas.
"""
import os
import uuid
from typing import Any, Dict, List, Optional
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

if not DB_URL:
    raise RuntimeError(
        "Falta la variable de entorno SUPABASE_DB_URL.\n"
        "Créala en tu .env con la connection string de Supabase."
    )

# Pool: mínimo 2 conexiones abiertas, máximo 10 simultáneas.
_pool: ThreadedConnectionPool = ThreadedConnectionPool(
    minconn=2,
    maxconn=10,
    dsn=DB_URL,
    cursor_factory=psycopg2.extras.RealDictCursor,
)

MAX_ITEMS_POR_PEDIDO = 15
MAX_TOTAL_POR_PEDIDO = 1000.0

def get_connection() -> psycopg2.extensions.connection:
    return _pool.getconn()

def release_connection(conn: psycopg2.extensions.connection) -> None:
    _pool.putconn(conn)

def _normalizar_telefono(telefono: str) -> str:
    return "".join(ch for ch in str(telefono) if ch.isdigit())

# ── INICIALIZACIÓN ──
def init_database() -> None:
    """Verifica que la conexión a Supabase funciona correctamente."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM productos")
        total = cursor.fetchone()["total"]
        print(f"✅ Conectado a Supabase. Productos en BD: {total}")
    except Exception as e:
        raise RuntimeError(f"❌ Error conectando a Supabase: {e}")
    finally:
        release_connection(conn)

# ── PRODUCTOS ──
def obtener_producto_por_nombre(nombre: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM productos WHERE LOWER(nombre) = LOWER(%s) LIMIT 1",
            (nombre.strip(),)
        )
        producto = cursor.fetchone()
        if not producto:
            return None

        cursor.execute(
            """
            SELECT i.id, i.nombre, i.precio_extra, i.disponible, pi.es_removible
            FROM ingredientes i
            INNER JOIN producto_ingredientes pi ON pi.ingrediente_id = i.id
            WHERE pi.producto_id = %s
            ORDER BY i.nombre
            """,
            (int(producto["id"]),)
        )
        ingredientes = [dict(fila) for fila in cursor.fetchall()]
        
        resultado = dict(producto)
        resultado["precio"] = resultado["precio_base"]
        resultado["ingredientes"] = [item["nombre"] for item in ingredientes]
        resultado["ingredientes_detalle"] = ingredientes
        resultado["disponible"] = bool(resultado["disponible"])
        return resultado
    finally:
        release_connection(conn)

def obtener_todos_productos() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos ORDER BY tipo, nombre")
        productos = cursor.fetchall()

        resultado: List[Dict[str, Any]] = []
        for producto in productos:
            info = dict(producto)
            info["precio"] = info["precio_base"]
            info["disponible"] = bool(info["disponible"])
            
            cursor.execute(
                """
                SELECT i.nombre
                FROM ingredientes i
                INNER JOIN producto_ingredientes pi ON pi.ingrediente_id = i.id
                WHERE pi.producto_id = %s
                """,
                (int(info["id"]),)
            )
            info["ingredientes"] = [fila["nombre"] for fila in cursor.fetchall()]
            resultado.append(info)
        return resultado
    finally:
        release_connection(conn)

# ── PEDIDOS ──
def obtener_pedido(pedido_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM pedidos WHERE pedido_id = %s LIMIT 1",
            (pedido_id.strip().upper(),)
        )
        pedido = cursor.fetchone()
        if not pedido:
            return None

        cursor.execute(
            """
            SELECT pi.id, pi.producto_id, p.nombre AS producto_nombre,
                   pi.cantidad, pi.precio_unitario_base
            FROM pedido_items pi
            INNER JOIN productos p ON p.id = pi.producto_id
            WHERE pi.pedido_id = %s
            ORDER BY pi.id
            """,
            (pedido_id.strip().upper(),)
        )
        resultado = dict(pedido)
        resultado["pago_validado"] = bool(resultado["pago_validado"])
        resultado["items"] = [dict(fila) for fila in cursor.fetchall()]
        return resultado
    finally:
        release_connection(conn)

def crear_nuevo_pedido(
    items_lista: List[str],
    cliente_telefono: Optional[str] = None,
    cliente_nombre: Optional[str] = None,
    tipo_entrega: str = "presencial",
    direccion: Optional[str] = None,
    numero_contacto: Optional[str] = None,
) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Validaciones iniciales
        if not items_lista:
            return {"error": "La lista de items no puede estar vacía."}
        if len(items_lista) > MAX_ITEMS_POR_PEDIDO:
            return {"error": f"El pedido supera el máximo de {MAX_ITEMS_POR_PEDIDO} productos."}

        # Gestión de cliente (Se omite la función helper interna _asegurar_cliente para brevedad, 
        # pero asume que tu lógica original de guardar/actualizar cliente va aquí).
        cliente_telefono_limpio = _normalizar_telefono(cliente_telefono) if cliente_telefono else ""
        
        total_productos = 0.0
        productos_validos = []

        for item_nombre in items_lista:
            producto = obtener_producto_por_nombre(item_nombre)
            if not producto:
                return {"error": f"Producto '{item_nombre}' no encontrado"}
            if not producto["disponible"]:
                return {"error": f"Producto '{producto['nombre']}' no disponible"}
            total_productos += float(producto["precio_base"])
            productos_validos.append(producto)

        if total_productos > MAX_TOTAL_POR_PEDIDO:
            return {"error": f"Total ${round(total_productos, 2)} MXN supera el máximo permitido."}

        pedido_id = f"PED-{uuid.uuid4().hex[:8].upper()}"
        costo_envio = 10.0 if tipo_entrega == "domicilio" else 0.0
        total_con_envio = round(total_productos + costo_envio, 2)

        # Inserción del pedido
        cursor.execute(
            """
            INSERT INTO pedidos (
                pedido_id, cliente_telefono, tipo_entrega, direccion_entrega, telefono_contacto_entrega,
                costo_envio, metodo_pago, pago_validado,
                total_productos, total_envio, descuento, total_final, estado
            ) VALUES (%s, %s, %s, %s, %s, %s, 'efectivo', 0, %s, %s, 0, %s, 'pendiente_validacion')
            """,
            (pedido_id, cliente_telefono_limpio or None, tipo_entrega, direccion, numero_contacto, costo_envio, total_productos, costo_envio, total_con_envio)
        )
        
        for producto in productos_validos:
            cursor.execute(
                "INSERT INTO pedido_items (pedido_id, producto_id, cantidad, precio_unitario_base) VALUES (%s, %s, 1, %s)",
                (pedido_id, producto["id"], float(producto["precio_base"]))
            )

        conn.commit()
        return {
            "exito": True,
            "pedido_id": pedido_id,
            "cliente_telefono": cliente_telefono_limpio or None,
            "cliente_nombre": cliente_nombre,
            "items": [p["nombre"] for p in productos_validos],
            "tipo_entrega": tipo_entrega,
            "direccion": direccion,
            "total_productos": round(total_productos, 2),
            "costo_envio": costo_envio,
            "total_final": total_con_envio,
            "estado": "pendiente_validacion",
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"Error al crear pedido: {str(e)}"}
    finally:
        release_connection(conn)

def actualizar_estado_pedido(pedido_id: str, nuevo_estado: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pedidos SET estado = %s WHERE pedido_id = %s",
            (nuevo_estado, pedido_id.strip().upper())
        )
        if cursor.rowcount == 0:
            return {"error": f"Pedido {pedido_id} no encontrado"}
        conn.commit()
        return {"exito": True, "pedido_id": pedido_id.strip().upper(), "estado": nuevo_estado}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        release_connection(conn)

# ── CLIENTES ──
def registrar_cliente_bd(nombre: str, telefono: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        telefono_limpio = _normalizar_telefono(telefono)
        cursor.execute(
            "INSERT INTO clientes (telefono, nombre, numero_contacto_llamada) VALUES (%s, %s, %s)",
            (telefono_limpio, nombre.strip(), telefono_limpio)
        )
        conn.commit()
        return {"exito": True, "cliente_id": telefono_limpio, "nombre": nombre.strip(), "telefono": telefono_limpio}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        release_connection(conn)

def obtener_historial_cliente(telefono: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        telefono_limpio = _normalizar_telefono(telefono)
        cursor.execute("SELECT * FROM clientes WHERE telefono = %s", (telefono_limpio,))
        cliente = cursor.fetchone()
        if not cliente:
            return {"error": f"Cliente con teléfono {telefono_limpio} no encontrado"}

        cursor.execute(
            """
            SELECT pedido_id, tipo_entrega, total_final, estado, hora_creacion
            FROM pedidos WHERE cliente_telefono = %s ORDER BY hora_creacion DESC
            """,
            (telefono_limpio,)
        )
        pedidos_raw = cursor.fetchall()
        
        pedidos = []
        for pedido in pedidos_raw:
            p = dict(pedido)
            cursor.execute(
                """
                SELECT p.nombre AS producto_nombre, pi.cantidad
                FROM pedido_items pi
                INNER JOIN productos p ON p.id = pi.producto_id
                WHERE pi.pedido_id = %s
                """,
                (p["pedido_id"],)
            )
            p["items"] = [dict(fila) for fila in cursor.fetchall()]
            pedidos.append(p)

        return {
            "cliente_id": cliente["telefono"],
            "nombre": cliente["nombre"],
            "telefono": cliente["telefono"],
            "direccion": cliente.get("direccion"),
            "total_pedidos": len(pedidos),
            "pedidos": pedidos,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        release_connection(conn)

def actualizar_direccion_cliente(telefono: str, direccion: str) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        telefono_limpio = _normalizar_telefono(telefono)
        cursor.execute(
            "UPDATE clientes SET direccion = %s WHERE telefono = %s",
            (direccion.strip(), telefono_limpio)
        )
        conn.commit()
        return {"exito": True, "direccion": direccion.strip()}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        release_connection(conn)