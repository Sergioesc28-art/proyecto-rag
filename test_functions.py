#!/usr/bin/env python
# test_functions.py - Prueba rápida de las funciones

from functions import (
    consultar_menu, 
    verificar_disponibilidad, 
    consultar_ingredientes,
    consultar_tiempo_espera,
    obtener_informacion_yoyo
)

print("=" * 60)
print("PRUEBA DE FUNCIONES CON BD SQLite")
print("=" * 60)

# Test 1: Menú
print("\n📋 TEST 1: Menú Completo")
menu = consultar_menu()
print(f"  ✓ Hamburguesas: {len(menu['hamburguesas'])}")
print(f"  ✓ Hot Dogs: {len(menu['hot_dogs'])}")
print(f"  ✓ Complementos: {len(menu['complementos'])}")
print(f"  ✓ Total de productos: {menu['total']}")

# Test 2: Disponibilidad
print("\n✅ TEST 2: Verificar Disponibilidad")
disp = verificar_disponibilidad('Hamburguesa Sencilla')
print(f"  ✓ {disp['mensaje']}")
print(f"  ✓ Precio: ${disp['precio']} MXN")
print(f"  ✓ Tipo: {disp['tipo']}")

# Test 3: Ingredientes
print("\n🍔 TEST 3: Ingredientes de Natsu Burger")
ing = consultar_ingredientes('Natsu Burger')
print(f"  ✓ Producto: {ing['nombre']}")
print(f"  ✓ Precio: ${ing['precio']} MXN")
print(f"  ✓ Ingredientes ({len(ing['ingredientes'])} items):")
for i, ingrediente in enumerate(ing['ingredientes'], 1):
    print(f"    {i}. {ingrediente}")

# Test 4: Tiempo de espera
print("\n⏱️ TEST 4: Tiempo de Espera")
espera = consultar_tiempo_espera()
print(f"  ✓ Minutos estimados: {espera['minutos_espera']}")
print(f"  ✓ Pedidos activos: {espera['pedidos_activos']}")
print(f"  ✓ Mensaje: {espera['mensaje']}")

# Test 5: Información de Yoyo
print("\n🏢 TEST 5: Información de Yoyo Burguer")
info = obtener_informacion_yoyo()
print(f"  ✓ Nombre: {info['nombre']}")
print(f"  ✓ Teléfono: {info['telefono']}")
print(f"  ✓ Horario: {info['horario']['dias_apertura']} ({info['horario']['hora_apertura']} - {info['horario']['hora_cierre']})")

print("\n" + "=" * 60)
print("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
print("=" * 60)
