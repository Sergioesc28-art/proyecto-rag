"""
database.py — Gestión de BD SQLite para Yoyo Burguer
Crea y gestiona las tablas de productos, pedidos y clientes
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "./yoyo_burguer.db"

# ── Inicializar base de datos ───────────────────────────────────
def init_database():
    """
    Crea las tablas de la BD si no existen.
    Llamar una sola vez al iniciar la app.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de productos/menú
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            precio REAL NOT NULL,
            tipo TEXT NOT NULL,
            disponible BOOLEAN DEFAULT 1,
            ingredientes TEXT NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de pedidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id TEXT UNIQUE NOT NULL,
            cliente_id INTEGER,
            total REAL NOT NULL,
            descuento REAL DEFAULT 0,
            total_final REAL NOT NULL,
            estado TEXT DEFAULT 'en_cocina',
            hora_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)
    
    # Tabla de items del pedido
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedido_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id TEXT NOT NULL,
            producto_nombre TEXT NOT NULL,
            cantidad INTEGER DEFAULT 1,
            precio_unitario REAL NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(pedido_id)
        )
    """)
    
    # Tabla de clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            telefono TEXT UNIQUE NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de descuentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS descuentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            porcentaje INTEGER NOT NULL,
            activo BOOLEAN DEFAULT 1
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")


# ── Cargar menú inicial ────────────────────────────────────────
def cargar_menu_inicial():
    """
    Inserta los productos de Yoyo Burguer en la BD.
    Se llama solo la primera vez.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar si ya existen productos
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] > 0:
        print("ℹ️  Menú ya existe en BD")
        conn.close()
        return
    
    # Datos del menú
    menu = [
        # HAMBURGUESAS
        ("Hamburguesa Sencilla", 33.00, "hamburguesa", True, 
         '["pan artesanal", "1 carne de res", "mayonesa", "lechuga", "jamón", "queso cheddar", "tocino"]'),
        ("Hamburguesa Doble Carne", 38.00, "hamburguesa", True,
         '["pan artesanal", "2 carnes de res", "mayonesa", "lechuga", "doble jamón", "queso cheddar", "tocino"]'),
        ("Hamburguesa Hawaiana", 39.00, "hamburguesa", True,
         '["pan artesanal", "1 carne de res", "mayonesa", "lechuga", "jamón extra", "queso cheddar", "tocino", "piña"]'),
        ("Hamburguesa Especial", 47.00, "hamburguesa", True,
         '["pan artesanal", "1 carne de res", "mayonesa", "lechuga", "doble jamón", "queso cheddar", "doble tocino", "piña", "salchicha de pavo"]'),
        ("Hamburguesa Especial Doble Carne", 55.00, "hamburguesa", True,
         '["pan artesanal", "2 carnes de res", "mayonesa", "lechuga", "doble jamón", "queso cheddar", "doble tocino", "piña", "salchicha de pavo"]'),
        ("Natsu Burger", 65.00, "hamburguesa", True,
         '["pan artesanal", "3 carnes de res", "mayonesa", "lechuga", "3 jamones", "queso cheddar", "3 tocinos", "piña", "salchicha de pavo", "cebolla caramelizada", "champiñones"]'),
        # HOT DOGS
        ("Hot Dog Sencillo", 19.00, "hot dog", True,
         '["pan tradicional", "1 salchicha de pavo", "mayonesa", "tocino", "cebolla"]'),
        ("Hot Dog Hawaiano", 22.00, "hot dog", True,
         '["pan tradicional", "1 salchicha de pavo", "mayonesa", "tocino extra", "cebolla", "piña"]'),
        ("Hot Dog Especial", 25.00, "hot dog", True,
         '["pan tradicional", "1 salchicha de pavo", "mayonesa", "tocino extra", "cebolla", "jamón", "queso cheddar"]'),
        ("Hot Dog Especial con Doble Salchicha", 28.00, "hot dog", True,
         '["pan tradicional", "2 salchichas de pavo", "mayonesa", "tocino extra", "cebolla", "jamón", "queso cheddar"]'),
        # COMPLEMENTOS
        ("Papas a la francesa", 50.00, "complemento", True, '["papas fritas"]'),
        ("Salchichas tipo pulpo", 30.00, "complemento", True, '["salchichas tipo pulpo"]'),
    ]
    
    cursor.executemany("""
        INSERT INTO productos (nombre, precio, tipo, disponible, ingredientes)
        VALUES (?, ?, ?, ?, ?)
    """, menu)
    
    # Insertar descuentos
    descuentos = [
        ("YOYO10", 10, True),
        ("PROMO20", 20, True),
        ("BIENVENIDO", 15, True),
    ]
    
    cursor.executemany("""
        INSERT INTO descuentos (codigo, porcentaje, activo)
        VALUES (?, ?, ?)
    """, descuentos)
    
    conn.commit()
    conn.close()
    print(f"✅ Menú cargado: {len(menu)} productos + {len(descuentos)} descuentos")


# ── Funciones auxiliares de BD ─────────────────────────────────

def get_connection():
    """Obtiene conexión a BD con row_factory como diccionario"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def obtener_producto_por_nombre(nombre: str) -> Optional[Dict[str, Any]]:
    """Obtiene un producto de la BD por nombre (case-insensitive)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM productos WHERE LOWER(nombre) = LOWER(?)", (nombre.strip(),))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        import json
        resultado = dict(resultado)
        resultado['ingredientes'] = json.loads(resultado['ingredientes'])
        return resultado
    return None


def obtener_todos_productos() -> List[Dict[str, Any]]:
    """Obtiene todos los productos de la BD"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM productos")
    resultados = cursor.fetchall()
    conn.close()
    
    import json
    productos = []
    for row in resultados:
        producto = dict(row)
        producto['ingredientes'] = json.loads(producto['ingredientes'])
        productos.append(producto)
    
    return productos


def obtener_pedido(pedido_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un pedido por su ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM pedidos WHERE pedido_id = ?", (pedido_id.upper(),))
    resultado = cursor.fetchone()
    conn.close()
    
    return dict(resultado) if resultado else None


def crear_nuevo_pedido(items_lista: List[str]) -> Dict[str, Any]:
    """
    Crea un nuevo pedido en la BD.
    Retorna el pedido_id o un error.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Validar items
        total = 0
        items_validos = []
        
        for item_nombre in items_lista:
            producto = obtener_producto_por_nombre(item_nombre)
            
            if not producto:
                return {"error": f"Producto '{item_nombre}' no encontrado"}
            
            if not producto['disponible']:
                return {"error": f"Producto '{producto['nombre']}' no disponible"}
            
            total += producto['precio']
            items_validos.append(producto)
        
        # Generar ID del pedido
        cursor.execute("SELECT COUNT(*) FROM pedidos")
        contador = cursor.fetchone()[0] + 1001
        pedido_id = f"PED-{contador}"
        
        # Insertar pedido
        cursor.execute("""
            INSERT INTO pedidos (pedido_id, total, total_final, estado)
            VALUES (?, ?, ?, 'en_cocina')
        """, (pedido_id, total, total))
        
        # Insertar items del pedido
        for producto in items_validos:
            cursor.execute("""
                INSERT INTO pedido_items (pedido_id, producto_nombre, precio_unitario)
                VALUES (?, ?, ?)
            """, (pedido_id, producto['nombre'], producto['precio']))
        
        conn.commit()
        
        return {
            "exito": True,
            "pedido_id": pedido_id,
            "items": [p['nombre'] for p in items_validos],
            "total": total,
            "estado": "en_cocina"
        }
    
    except Exception as e:
        conn.rollback()
        return {"error": f"Error al crear pedido: {str(e)}"}
    
    finally:
        conn.close()


def actualizar_estado_pedido(pedido_id: str, nuevo_estado: str) -> Dict[str, Any]:
    """Actualiza el estado de un pedido"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE pedidos SET estado = ? WHERE pedido_id = ?", 
                      (nuevo_estado, pedido_id.upper()))
        
        if cursor.rowcount == 0:
            return {"error": f"Pedido {pedido_id} no encontrado"}
        
        conn.commit()
        return {"exito": True, "pedido_id": pedido_id, "estado": nuevo_estado}
    
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    
    finally:
        conn.close()


def aplicar_descuento_a_pedido(pedido_id: str, codigo: str) -> Dict[str, Any]:
    """Aplica un descuento a un pedido"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener porcentaje del descuento
        cursor.execute("SELECT porcentaje FROM descuentos WHERE UPPER(codigo) = UPPER(?) AND activo = 1",
                      (codigo.strip(),))
        resultado = cursor.fetchone()
        
        if not resultado:
            return {"error": f"Código '{codigo}' no válido"}
        
        porcentaje = resultado[0]
        
        # Obtener pedido
        cursor.execute("SELECT * FROM pedidos WHERE pedido_id = ?", (pedido_id.upper(),))
        pedido = cursor.fetchone()
        
        if not pedido:
            return {"error": f"Pedido '{pedido_id}' no encontrado"}
        
        # Calcular descuento
        total = pedido['total']
        descuento = round(total * porcentaje / 100)
        total_final = total - descuento
        
        # Actualizar pedido
        cursor.execute("UPDATE pedidos SET descuento = ?, total_final = ? WHERE pedido_id = ?",
                      (descuento, total_final, pedido_id.upper()))
        
        conn.commit()
        
        return {
            "exito": True,
            "pedido_id": pedido_id,
            "porcentaje": porcentaje,
            "descuento": descuento,
            "total_anterior": total,
            "total_final": total_final
        }
    
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    
    finally:
        conn.close()


def registrar_cliente_bd(nombre: str, telefono: str) -> Dict[str, Any]:
    """Registra un nuevo cliente en la BD"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Validar teléfono
        telefono_limpio = telefono.strip().replace("-", "").replace(" ", "")
        
        if len(telefono_limpio) != 10 or not telefono_limpio.isdigit():
            return {"error": "El teléfono debe tener exactamente 10 dígitos"}
        
        # Verificar si ya existe
        cursor.execute("SELECT * FROM clientes WHERE telefono = ?", (telefono_limpio,))
        if cursor.fetchone():
            return {"error": f"Teléfono {telefono_limpio} ya está registrado"}
        
        # Insertar cliente
        cliente_id = f"CLI-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute("""
            INSERT INTO clientes (cliente_id, nombre, telefono)
            VALUES (?, ?, ?)
        """, (cliente_id, nombre.strip(), telefono_limpio))
        
        conn.commit()
        
        return {
            "exito": True,
            "cliente_id": cliente_id,
            "nombre": nombre,
            "telefono": telefono_limpio
        }
    
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    
    finally:
        conn.close()


def obtener_historial_cliente(telefono: str) -> Dict[str, Any]:
    """Obtiene el historial de pedidos de un cliente"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        telefono_limpio = telefono.strip().replace("-", "").replace(" ", "")
        
        # Obtener cliente
        cursor.execute("SELECT * FROM clientes WHERE telefono = ?", (telefono_limpio,))
        cliente = cursor.fetchone()
        
        if not cliente:
            return {"error": f"Cliente con teléfono {telefono_limpio} no encontrado"}
        
        # Obtener pedidos del cliente
        cursor.execute("SELECT * FROM pedidos WHERE cliente_id = ? ORDER BY hora_creacion DESC",
                      (cliente['id'],))
        pedidos = cursor.fetchall()
        
        return {
            "cliente_id": cliente['cliente_id'],
            "nombre": cliente['nombre'],
            "telefono": cliente['telefono'],
            "total_pedidos": len(pedidos),
            "pedidos": [dict(p) for p in pedidos]
        }
    
    except Exception as e:
        return {"error": str(e)}
    
    finally:
        conn.close()
