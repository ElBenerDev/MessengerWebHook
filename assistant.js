import { OpenAI, AssistantEventHandler } from 'openai';
import { override } from 'typing-extensions';

// Configuramos el cliente de OpenAI
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const assistantId = process.env.ASSISTANT_ID;

// Crear y manejar el hilo de conversación
const thread = await client.beta.threads.create();
console.log('Hilo creado:', thread);

// Manejador de eventos para manejar la respuesta del asistente
class EventHandler extends AssistantEventHandler {
  @override
  on_text_created(text) {
    // Este evento se dispara cuando se crea texto en el flujo
    return text.value; // Retornamos el texto generado
  }

  @override
  on_text_delta(delta, snapshot) {
    // Este evento se dispara cuando el texto cambia o se agrega en el flujo
    return delta.value; // Retornamos el texto parcial generado
  }
}

// Función para manejar los mensajes del usuario
export async function handleUserMessage(userMessage) {
  try {
    const responseChunks = [];
    const eventHandler = new EventHandler();

    // Enviar el mensaje del usuario al asistente
    await client.beta.threads.messages.create({
      thread_id: thread.id,
      role: 'user',
      content: userMessage,
    });

    // Crear y manejar la respuesta del asistente
    await client.beta.threads.runs.stream(
      {
        thread_id: thread.id,
        assistant_id: assistantId,
        event_handler: eventHandler,
      },
      {
        onData: (data) => responseChunks.push(data),
      }
    );

    return responseChunks.join(''); // Retornamos la respuesta completa
  } catch (error) {
    console.error('Error en handleUserMessage:', error);
    throw new Error('Error al generar la respuesta del asistente.');
  }
}
