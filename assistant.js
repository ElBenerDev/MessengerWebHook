import { OpenAI } from 'openai';

// Configuración del cliente OpenAI
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const assistantId = 'asst_Q3M9vDA4aN89qQNH1tDXhjaE';

// Función para manejar mensajes del usuario
export async function handleUserMessage(userMessage) {
  try {
    // Crear un hilo de conversación
    const thread = await client.beta.threads.create();

    // Enviar el mensaje del usuario al hilo
    await client.beta.threads.messages.create({
      thread_id: thread.id,
      role: 'user',
      content: userMessage,
    });

    // Obtener la respuesta del asistente
    let assistantResponse = '';
    await client.beta.threads.runs.stream(
      {
        thread_id: thread.id,
        assistant_id: assistantId,
      },
      {
        onData: (data) => {
          assistantResponse += data.value; // Acumular el texto recibido
        },
      }
    );

    return assistantResponse.trim(); // Retornar la respuesta completa
  } catch (error) {
    console.error('Error en handleUserMessage:', error.message);
    throw new Error('No se pudo procesar el mensaje.');
  }
}
