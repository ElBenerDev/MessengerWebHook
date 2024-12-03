import { OpenAI } from 'openai';
import dotenv from 'dotenv';

// Cargar las variables de entorno desde el archivo .env
dotenv.config();

// Configurar el cliente de OpenAI
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Función para interactuar con el asistente
export async function interactWithAssistant(userMessage) {
  const assistantId = 'asst_Q3M9vDA4aN89qQNH1tDXhjaE';

  try {
    // Crear un hilo y obtener una respuesta
    const thread = await client.chat.completions.create({
      model: 'gpt-4',
      messages: [
        { role: 'user', content: userMessage },
      ],
    });

    return thread.choices[0].message.content; // Retorna la respuesta del asistente
  } catch (error) {
    console.error('Error al interactuar con el asistente:', error);
    throw error; // Propaga el error para manejarlo en el servidor
  }
}
