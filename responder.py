import requests
from query import buscar_contexto

# URL del servidor llama.cpp
LLAMA_URL = "http://127.0.0.1:8080/v1/chat/completions"

def responder(pregunta):

    # Buscar contexto en ChromaDB
    contexto = buscar_contexto(pregunta)


    # Prompt del sistema
    prompt_sistema = """
Eres un asistente que responde preguntas usando únicamente el contexto proporcionado.

Si encuentras información relacionada en el contexto, responde de manera clara y directa.

Si realmente no existe información suficiente, responde:
'No encontré información sobre eso en la base de datos.'

No inventes información externa.
"""

    # Payload para llama.cpp
    payload = {
        "messages": [
            {
                "role": "system",
                "content": prompt_sistema
            },
            {
                "role": "user",
                "content": f"Contexto:\n{contexto}\n\nPregunta: {pregunta}"
            }
        ],
        "max_tokens": 512,
        "temperature": 0.0,
        "stream": False
    }

    # Enviar petición al servidor
    respuesta = requests.post(
        LLAMA_URL,
        json=payload
    )

    # Convertir respuesta JSON
    resultado = respuesta.json()

    # Obtener texto generado
    return resultado["choices"][0]["message"]["content"]


# Programa principal
if __name__ == "__main__":

    while True:

        pregunta = input("\nPregunta (o escribe 'salir'): ")

        if pregunta.lower() == "salir":
            break

        respuesta = responder(pregunta)

        print("\n🤖 Respuesta:")
        print(respuesta)