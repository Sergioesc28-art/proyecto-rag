#!/usr/bin/env python
# validate_tools_schema.py

import json

print("=" * 60)
print("VALIDACIÓN DE tools_schema.json")
print("=" * 60)

try:
    with open('tools_schema.json', 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    print(f"\n✅ JSON válido")
    print(f"\n📋 Total de herramientas: {len(tools)}\n")
    
    for i, tool in enumerate(tools, 1):
        func = tool.get('function', {})
        name = func.get('name', 'SIN_NOMBRE')
        description = func.get('description', '')[:50]
        params = func.get('parameters', {}).get('properties', {})
        required = func.get('parameters', {}).get('required', [])
        
        print(f"{i:2}. {name}")
        print(f"    📝 {description}...")
        print(f"    ⚙️  Parámetros requeridos: {required if required else 'Ninguno'}")
        print()
    
    print("=" * 60)
    print("✅ VALIDACIÓN EXITOSA")
    print("=" * 60)
    
except json.JSONDecodeError as e:
    print(f"❌ Error de JSON: {e}")
except FileNotFoundError:
    print("❌ Archivo tools_schema.json no encontrado")
except Exception as e:
    print(f"❌ Error: {e}")
