# 🍔 Yoyo Burguer - RAG + Function Calling con Llama 3.2 8B

Sistema inteligente de gestión de pedidos para Yoyo Burguer combinando **Retrieval Augmented Generation (RAG)** con **Function Calling** en Llama 3.2 8B local.

## ✨ Características

### 🤖 Function Calling (12 Funciones)
- **Consultar Menú**: Ver todos los productos con precios
- **Verificar Disponibilidad**: Chequear stock en tiempo real
- **Consultar Ingredientes**: Detalles completos de cada producto
- **Crear Pedido**: Registrar nuevas órdenes en BD
- **Consultar Estado**: Seguimiento de pedidos (en cocina, listo, entregado)
- **Cancelar Pedido**: Anular órdenes activas
- **Aplicar Descuento**: Códigos YOYO10 (10%), PROMO20 (20%), BIENVENIDO (15%)
- **Tiempo de Espera**: Estimado dinámico basado en carga
- **Registrar Cliente**: Guardar clientes con teléfono
- **Historial Cliente**: Ver pedidos anteriores
- **Información Yoyo**: Horarios, ubicación, políticas
- **Complementos**: Lista de guarniciones

### 📚 RAG Vectorial
- **ChromaDB**: 53 vectores de 3 PDFs
- **Detección de Cambios**: Sistema inteligente que evita duplicados
- **Metadata**: Hashes SHA256 para versionado
- **Actualización Incremental**: Solo reindexa PDFs modificados

### 💾 Base de Datos
- **SQLite**: Persistencia transaccional
- **5 Tablas**: productos, pedidos, pedido_items, clientes, descuentos
- **12 Productos**: Hamburguesas, Hot Dogs, Complementos
- **Precios**: $19-$65 MXN

### 🎯 Llama 3.2 8B Integration
- **Tool Calling**: Intercepción automática de tool_calls
- **Error Handling**: Captura de excepciones sin romper chat
- **Segunda Ronda**: Procesa resultados de tools para respuesta final
- **Prompt Inteligente**: Sistema que entiende contexto de negocio

---

## 📋 Estructura del Proyecto

```
proyecto-rag/
├── 📄 README.md                          # Este archivo
├── 🔐 .gitignore                         # Archivos ignorados por git
│
├── 🔧 Código Principal
│   ├── app.py                            # Streamlit + Tool Calling
│   ├── functions.py                      # 12 funciones de Yoyo Burguer
│   ├── database.py                       # SQLite con 10 helper functions
│   ├── ingest.py                         # RAG con detección de cambios
│   ├── query.py                          # Búsqueda vectorial ChromaDB
│   └── responder.py                      # Generación de respuestas RAG
│
├── 🧪 Testing & Validation
│   ├── test_functions.py                 # Suite de pruebas de funciones
│   └── validate_tools.py                 # Validación JSON Schema
│
├── 📊 Configuración & Schema
│   ├── tools_schema.json                 # Schema OpenAI para 12 funciones
│   ├── ingest_metadata.json              # Hashes de PDFs (generado)
│   └── yoyo_burguer.db                   # BD SQLite (generado)
│
├── 📁 Datos
│   ├── pdfs/                             # 3 PDFs de Yoyo Burguer
│   │   ├── 01_Operativa_YoyoBurguer.pdf
│   │   ├── 02_Menu_YoyoBurguer.pdf
│   │   └── 03_PreguntasFrecuentes_YoyoBurguer.pdf
│   │
│   └── chroma_db/                        # Vector store (generado)
│       └── 53 vectores indexados
│
└── 📦 requirements.txt                   # Dependencias
```

---

## 🚀 Instalación

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tuusuario/proyecto-rag.git
cd proyecto-rag/proyecto-rag
```

### 2. Crear Entorno Virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Inicializar Base de Datos
```bash
python -c "from database import init_database, cargar_menu_inicial; init_database(); cargar_menu_inicial()"
```

### 5. Indexar PDFs en ChromaDB
```bash
python ingest.py
```

---

## 🎮 Uso

### Terminal 1 - Iniciar Llama 3.2 8B
```bash
ollama run llama2:13b-chat-q4_K_M --port 8080
```

### Terminal 2 - Iniciar Streamlit
```bash
streamlit run app.py
```

Se abrirá en: `http://localhost:8501`

---

## 💬 Ejemplos de Uso

### Ejemplo 1: Consultar Menú
```
Usuario: "¿Cuál es el menú de Yoyo?"
→ Llama ejecuta: consultar_menu()
→ Respuesta: Lista completa de 12 productos con precios
```

### Ejemplo 2: Crear Pedido
```
Usuario: "Quiero una hamburguesa sencilla y papas"
→ Llama ejecuta: crear_pedido(['Hamburguesa Sencilla', 'Papas a la francesa'])
→ BD: Inserta en tabla pedidos
→ Respuesta: "Tu pedido PED-1002 está listo. Total: $83 MXN"
```

### Ejemplo 3: Aplicar Descuento
```
Usuario: "Tengo código YOYO10"
→ Llama ejecuta: aplicar_descuento('PED-1002', 'YOYO10')
→ Respuesta: "Descuento del 10% aplicado. Nuevo total: $74.70 MXN"
```

---

## 🔍 Características Avanzadas

### Detección Inteligente de Cambios en PDFs
```bash
# Cambiar un PDF
# Ejecutar ingest.py
python ingest.py
```

**Resultado**:
```
🔄 02_Menu_YoyoBurguer.pdf: CAMBIOS DETECTADOS
   → Eliminando 8 vectores viejos...
   → Generando 12 fragmentos nuevos...
   → Agregados 12 vectores a ChromaDB
```

### Validación de Funciones
```bash
python test_functions.py
python validate_tools.py
```

---

## 📊 Rúbrica de Proyecto

- ✅ **7-15 funciones**: 12 funciones implementadas
- ✅ **Type hints**: Todos los parámetros tipados
- ✅ **Docstrings**: Google-style con Args/Returns
- ✅ **JSON Schema tools**: tools_schema.json validado
- ✅ **Llama 3.2 8B**: Integración completa
- ✅ **Function calling**: Interceptor + ejecutor
- ✅ **Error handling**: Try/except en toda la cadena
- ✅ **BD persistente**: SQLite con 5 tablas

---

## 🛠️ Tecnologías

| Componente | Tecnología | Descripción |
|-----------|-----------|-------------|
| **LLM** | Llama 3.2 8B | Modelo de lenguaje local |
| **Vector DB** | ChromaDB | Almacén de embeddings |
| **SQL DB** | SQLite3 | Base de datos transaccional |
| **Embeddings** | Sentence Transformers | all-MiniLM-L6-v2 |
| **Frontend** | Streamlit | Interfaz web |
| **PDF** | PyPDF | Extracción de texto |

---

## 📝 Notas de Desarrollo

### Estructura de Respuesta de Function Calling
```python
# Llama retorna:
{
    "tool_calls": [
        {
            "function": {
                "name": "crear_pedido",
                "arguments": "{\"items\": [\"Hamburguesa Sencilla\"]}"
            }
        }
    ]
}

# app.py ejecuta y retorna resultado
# Llama genera respuesta final basada en resultado
```

### Opciones de Mejora Futura
- [ ] Autenticación de usuarios
- [ ] Integración con métodos de pago reales
- [ ] Dashboard de estadísticas
- [ ] Notificaciones en tiempo real
- [ ] Soporte multiidioma
- [ ] API REST (FastAPI)

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver `LICENSE` para detalles.

---

## 👥 Autor

**Sergi Pérez** - Desarrollo de Sistema RAG + Function Calling para Yoyo Burguer

---

## 📞 Soporte

Para problemas o preguntas:
- Abre un Issue en GitHub
- Verifica que Llama 3.2 8B esté corriendo en el puerto 8080
- Confirma que SQLite está inicializado: `python -c "from database import get_connection; print(get_connection())"`

---

## 🎯 Próximos Pasos

1. ✅ Versionar en GitHub
2. ⏳ Agregar autenticación
3. ⏳ Crear API REST
4. ⏳ Dashboard de estadísticas
5. ⏳ Integración con pagos

---

**Última actualización**: 26 de mayo de 2026
