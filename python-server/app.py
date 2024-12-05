from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
from dotenv import load_dotenv
import os

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Obtener la clave de la API desde las variables de entorno
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("La clave de la API de OpenAI no está configurada. Asegúrate de definir OPENAI_API_KEY en tu archivo .env.")

# Configura tu cliente con la API key
client = OpenAI(api_key=api_key)

# Crear un asistente y un hilo de conversación
assistant_id = "asst_Q3M9vDA4aN89qQNH1tDXhjaE"
thread = client.beta.threads.create()
print("Hilo creado:", thread)

# Crear un manejador de eventos para manejar el stream de respuestas del asistente
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        # Este evento se dispara cuando se crea texto en el flujo
        print(f"Asistente: {text.value}", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        # Este evento se dispara cuando el texto cambia o se agrega en el flujo
        print(delta.value, end="", flush=True)

# Función para mantener la conversación dentro del mismo hilo
def continue_conversation():
    while True:
        # Pedir input del usuario
        user_message = input("\nTú: ")

        if user_message.lower() == "salir":
            print("Terminando conversación...")
            break

        # Enviar mensaje del usuario al hilo
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        # Crear y manejar la respuesta del asistente
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant_id,
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()

# Iniciar la conversación continua
continue_conversation()