import os
import json
import re
import requests

LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:11434/v1/chat/completions")

def sanitizar_respuesta(texto: str) -> str:
    """Limpia fugas de tokens o palabras clave técnicas de la respuesta del LLM."""
    reemplazos = {
        r'\b(función|herramienta|tool|API|tool_call|JSON|parámetros)\b': ''
    }
    texto_limpio = texto
    for patron, reemplazo in reemplazos.items():
        texto_limpio = re.sub(patron, reemplazo, texto_limpio, flags=re.IGNORECASE)
    return re.sub(r'[ \t]+', ' ', texto_limpio).strip()

def generar_respuesta_llm(
    pregunta: str,
    historial: list,
    contexto_rag: str,
    prompt_sistema: str,
    tools_schema: list,
    ejecutor_herramientas, # Función para procesar las tools
    telefono_cliente: str | None = None,
    nombre_cliente: str | None = None
) -> tuple[str, list | None]:
    """
    Maneja el ciclo completo de petición a Qwen2.5:3b, incluyendo la 
    resolución de tool calls en una segunda ronda si es necesario.
    """
    messages = [{"role": "system", "content": prompt_sistema}]
    
    # Historial reciente (últimos 10 mensajes)
    historial_reciente = historial[-11:-1] if len(historial) > 1 else []
    for msg in historial_reciente:
        messages.append({"role": msg["rol"], "content": msg["texto"]})

    messages.append({"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"})

    payload = {
        "model": "qwen2.5:3b",
        "messages": messages,
        "tools": tools_schema,
        "tool_choice": "auto",
        "temperature": 0.1,
        "max_tokens": 512,
        "stream": False
    }

    try:
        respuesta = requests.post(LLAMA_URL, json=payload, timeout=120)
        respuesta.raise_for_status()
        resultado_inicial = respuesta.json()
    except requests.RequestException as e:
        return f"❌ Error conectando con Ollama: {e}", None

    if "choices" not in resultado_inicial or not resultado_inicial["choices"]:
        return "❌ Error de Ollama: respuesta vacía o malformada.", None

    mensaje_respuesta = resultado_inicial["choices"][0]["message"]

    # ── FLUJO: Si la IA decide usar herramientas ──
    if "tool_calls" in mensaje_respuesta:
        tool_calls = mensaje_respuesta["tool_calls"]
        resultados_tools = []

        for tool_call in tool_calls:
            nombre_herramienta = tool_call["function"]["name"]
            args_json = tool_call["function"]["arguments"]
            argumentos = json.loads(args_json) if isinstance(args_json, str) else args_json

            # PROTECCIÓN: Auto-inyección de datos seguros del cliente
            if nombre_herramienta == "consultar_historial_cliente":
                if not telefono_cliente:
                    return "Por políticas de privacidad, no puedo mostrar historiales. Por favor ingresa tu número de cuenta.", None
                argumentos["telefono"] = telefono_cliente

            elif nombre_herramienta in ["crear_pedido", "registrar_cliente"]:
                if telefono_cliente and not argumentos.get("telefono"):
                    argumentos["telefono"] = telefono_cliente
                if nombre_cliente and not argumentos.get("nombre"):
                    argumentos["nombre"] = nombre_cliente

            # Ejecutar la herramienta mediante el callback
            resultado_ejecucion = ejecutor_herramientas(nombre_herramienta, argumentos)
            resultados_tools.append({
                "tool_name": nombre_herramienta,
                "arguments": argumentos,
                "result": resultado_ejecucion
            })

        # Segunda ronda al LLM con los resultados de las herramientas
        mensajes_segunda_ronda = messages + [mensaje_respuesta]
        for tool_result in resultados_tools:
            mensajes_segunda_ronda.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_name"],
                "content": json.dumps(tool_result["result"], ensure_ascii=False, default=str)
            })

        payload_segunda = {
            "model": "qwen2.5:3b",
            "messages": mensajes_segunda_ronda,
            "temperature": 0.1,
            "max_tokens": 512,
            "stream": False
        }

        try:
            respuesta_final = requests.post(LLAMA_URL, json=payload_segunda, timeout=60)
            respuesta_final.raise_for_status()
            texto_respuesta = respuesta_final.json()["choices"][0]["message"]["content"]
        except Exception as e:
            texto_respuesta = f"Error en segunda llamada a Llama: {e}"

        return sanitizar_respuesta(texto_respuesta), resultados_tools

    # ── FLUJO NORMAL: Si no hay herramientas, devuelve texto directo ──
    else:
        return sanitizar_respuesta(mensaje_respuesta.get("content", "Sin respuesta")), None