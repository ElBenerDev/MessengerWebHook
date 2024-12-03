import { OpenAI } from 'openai';

// Configura el cliente de OpenAI
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const assistantId = 'asst_Q3M9vDA4aN89qQNH1tDXhjaE'; // ID del asistente

// Función para manejar el mensaje del usuario y obtener respuesta
export async function handleUserMessage(userMessage) {
  try {
    // Crear un hilo para la conversación
    const thread = await client.beta.threads.create();

    // Enviar el mensaje del usuario con el 'role' correcto
    await client.beta.threads.messages.create({
      thread_id: thread.id,
      role: 'user',  // Especificar que el mensaje es del usuario
      content: userMessage,
    });

    // Capturar la respuesta del asistente
    let assistantResponse = '';
    await client.beta.threads.runs.stream(
      {
        thread_id: thread.id,
        assistant_id: assistantId,
      },
      {
        onData: (data) => {
          assistantResponse += data.value; // Acumulamos la respuesta
        },
      }
    );

    return assistantResponse.trim();  // Retornamos la respuesta procesada
  } catch (error) {
    console.error('Error en handleUserMessage:', error.message);
    throw new Error('No se pudo procesar el mensaje.');
  }
}
