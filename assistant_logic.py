from flask import Flask, request, jsonify
import logging
import openai
import httpx

# Configuración básica
app = Flask(__name__)

# Configuración de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diccionario para mantener el estado de los hilos de conversación con los usuarios
user_threads = {}

# Identificación del asistente (puedes reemplazarla con tu propio asistente o cliente)
assistant_id = "tu_assistant_id"

# Configura tu clave de API de OpenAI
openai.api_key = 'tu_api_key'

# Función que maneja la respuesta del asistente
def handle_assistant_response(user_message, user_id):
    """ Maneja la respuesta del asistente de OpenAI. """
    try:
        # Verificar si ya existe un thread_id para este usuario
        if user_id not in user_threads:
            # Crear un nuevo hilo de conversación
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Eres un asistente útil."}]
            )
            thread_id = response['id']
            logger.info(f"Hilo creado para el usuario {user_id}: {thread_id}")
            user_threads[user_id] = thread_id
        else:
            thread_id = user_threads[user_id]

        # Enviar el mensaje del usuario al hilo existente
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": user_message}
            ],
            thread_id=thread_id
        )

        assistant_message = response['choices'][0]['message']['content'].strip()
        logger.info(f"Mensaje generado por el asistente: {assistant_message}")

        if assistant_message:
            return assistant_message, user_id
        else:
            return "Hubo un problema al procesar tu mensaje.", user_id

    except Exception as e:
        logger.error(f"Error al generar respuesta: {str(e)}")
        return "Hubo un problema al procesar tu mensaje.", user_id


# Ruta que recibe los mensajes del webhook de WhatsApp
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    logger.info(f"Webhook recibido: {data}")

    # Extraer el mensaje del usuario y su ID
    user_message = data['messages'][0]['text']['body']
    user_id = data['contacts'][0]['wa_id']

    # Procesar el mensaje con el asistente
    assistant_response, user_id = handle_assistant_response(user_message, user_id)

    # Enviar la respuesta al usuario a través de WhatsApp
    send_whatsapp_message(user_id, assistant_response)

    return jsonify({'status': 'success'})


# Función para enviar el mensaje al usuario de WhatsApp
def send_whatsapp_message(user_id, message):
    """ Envia un mensaje de texto a través de la API de WhatsApp Business. """
    try:
        url = "https://graph.facebook.com/v13.0/your_phone_number_id/messages"
        headers = {
            "Authorization": f"Bearer your_access_token",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": user_id,
            "text": {"body": message}
        }
        response = httpx.post(url, headers=headers, json=data)
        logger.info(f"Mensaje enviado a {user_id}: {message}")
    except Exception as e:
        logger.error(f"Error al enviar mensaje a {user_id}: {str(e)}")


# Ruta principal para verificar si la app está funcionando
@app.route('/')
def index():
    return "¡El servicio está en vivo!"


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
