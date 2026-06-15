import os
import json
import re
import requests

LLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"

def sanitizar_respuesta(texto: str) -> str:
    reemplazos = { r'\b(función|herramienta|tool|API|tool_call|JSON|parámetros)\b': '' }
    texto_limpio = texto.replace("`", "") # Adiós al Markdown verde de Streamlit
    for patron, reemplazo in reemplazos.items():
        texto_limpio = re.sub(patron, reemplazo, texto_limpio, flags=re.IGNORECASE)
    return re.sub(r'[ \t]+', ' ', texto_limpio).strip()

def generar_respuesta_llm_stream(
    pregunta: str,
    historial: list,
    contexto_rag: str,
    prompt_sistema: str,
    tools_schema: list,
    ejecutor_herramientas,
    telefono_cliente: str | None = None,
    nombre_cliente: str | None = None
):
    """
    Retorna un generador (Yield) para que Streamlit imprima la respuesta letra por letra,
    además de la lista de herramientas ejecutadas.
    """
    messages = [{"role": "system", "content": prompt_sistema}]
    
    # Reducir historial a los últimos 4 mensajes (optimiza memoria y atención del LLM)
    historial_reciente = historial[-5:-1] if len(historial) > 1 else []
    for msg in historial_reciente:
        messages.append({"role": msg["rol"], "content": msg["texto"]})

    messages.append({"role": "user", "content": f"Contexto de BD:\n{contexto_rag}\n\nPregunta: {pregunta}"})

    # PRIMERA LLAMADA: Revisar si quiere usar herramientas (sin stream)
    payload_tools = {
        "model": "qwen2.5:3b",
        "messages": messages,
        "tools": tools_schema,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 512,
        "stream": False
    }

    try:
        respuesta_inicial = requests.post(LLAMA_URL, json=payload_tools, timeout=120)
        respuesta_inicial.raise_for_status()
        respuesta = respuesta_inicial.json()
    except Exception as e:
        def error_gen(): yield f"❌ Error conectando con Ollama: {e}"
        return error_gen(), None

    mensaje_respuesta = respuesta["choices"][0]["message"]
    resultados_tools = None

    if "tool_calls" in mensaje_respuesta:
        tool_calls = mensaje_respuesta["tool_calls"]
        resultados_tools = []

        for tool_call in tool_calls:
            nombre_herramienta = tool_call["function"]["name"]
            # Extraemos el ID real si el modelo lo provee, si no, usamos el nombre como fallback
            tool_id = tool_call.get("id", nombre_herramienta) 
            args_json = tool_call["function"]["arguments"]
            argumentos = json.loads(args_json) if isinstance(args_json, str) else args_json

            # Protecciones de datos...
            if nombre_herramienta == "consultar_historial_cliente" and telefono_cliente:
                argumentos["telefono"] = telefono_cliente
            elif nombre_herramienta in ["crear_pedido", "registrar_cliente"]:
                if telefono_cliente: argumentos["telefono"] = telefono_cliente
                if nombre_cliente: argumentos["nombre"] = nombre_cliente

            resultado_ejecucion = ejecutor_herramientas(nombre_herramienta, argumentos)
            resultados_tools.append({
                "tool_call_id": tool_id,
                "tool_name": nombre_herramienta,
                "arguments": argumentos,
                "result": resultado_ejecucion
            })

        # Preparamos la segunda llamada con los resultados
        messages.append(mensaje_respuesta)
        for tool_result in resultados_tools:
            
            # ── ESCUDO ANTI-ALUCINACIONES ──
            # Enmascaramos el JSON gigante para no saturar al LLM.
            # Streamlit seguirá teniendo los datos reales en 'resultados_tools'.
            datos_para_llm = tool_result["result"]
            
            if tool_result["tool_name"] == "consultar_historial_cliente":
                datos_para_llm = {
                    "exito": True, 
                    "instruccion_interna": "El sistema visual ya mostró las tarjetas. Responde ÚNICAMENTE con: 'Aquí tienes tus últimos pedidos. ¿En qué más te puedo ayudar?' NO inventes IDs ni listes productos."
                }


            messages.append({
                "role": "tool",
                "tool_call_id": tool_result["tool_call_id"],
                "content": json.dumps(datos_para_llm, ensure_ascii=False, default=str)
            })
            
    # LLAMADA FINAL CON STREAMING
    payload_final = {
        "model": "qwen2.5:3b",
        "messages": messages,
        "temperature": 0.2,
        "stream": True 
    }

    try:
        respuesta_stream = requests.post(LLAMA_URL, json=payload_final, stream=True, timeout=120)
        respuesta_stream.raise_for_status()
    except Exception as e:
        def error_gen(): yield f"❌ Error en el streaming: {e}"
        return error_gen(), resultados_tools
    
    # ── EL NUEVO GENERADOR ADAPTADO A SSE ──
    def generador_texto():
        for linea in respuesta_stream.iter_lines():
            if not linea:
                continue
            
            linea_str = linea.decode("utf-8").strip()
            
            # Limpiamos el prefijo 'data: '
            if linea_str.startswith("data: "):
                linea_str = linea_str[6:]
                
            # Detenemos el generador si el servidor indica que terminó
            if linea_str == "[DONE]":
                break
                
            try:
                datos = json.loads(linea_str)
                # El formato stream guarda el texto en 'delta', no en 'message'
                if "choices" in datos and len(datos["choices"]) > 0:
                    delta = datos["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        yield delta["content"].replace("`", "")
            except json.JSONDecodeError:
                # Ignoramos silenciosamente líneas malformadas para no romper la UI
                continue

    return generador_texto(), resultados_tools