import { OpenAI } from 'openai';

// Configuramos el cliente de OpenAI
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const assistantId = process.env.ASSISTANT_ID;

// Crear y manejar el hilo de conversación
const thread = await client.beta.threads.create();
console.log('Hilo creado:', thread);

// Función para manejar los mensajes del usuario
export async function handleUserMessage(userMessage) {
  try {
    const responseChunks = [];

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
      },
      {
        onData: (data) => responseChunks.push(data.value), // Capturamos el contenido del texto
      }
    );

    return responseChunks.join(''); // Retornamos la respuesta completa
  } catch (error) {
    console.error('Error en handleUserMessage:', error);
    throw new Error('Error al generar la respuesta del asistente.');
  }
}
