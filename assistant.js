import { OpenAI } from 'openai';
import dotenv from 'dotenv';

// Cargar variables de entorno
dotenv.config();

// Crear cliente de OpenAI con la clave de la API
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,  // La API Key debe estar en .env
});

// Crear un hilo de conversación
let threadId = null;

// Configurar el manejador de eventos
class EventHandler {
  // Evento cuando el asistente envía texto
  onTextCreated(text) {
    console.log(`Asistente: ${text}`);
  }

  // Evento cuando hay un cambio en el texto del asistente
  onTextDelta(delta, snapshot) {
    if (delta && delta.value) {
      process.stdout.write(delta.value);
    }
  }

  // Evento cuando se llama a una herramienta
  onToolCallCreated(toolCall) {
    console.log(`\nAsistente > ${toolCall.type}`);
  }

  // Manejo de la salida de herramientas
  onToolCallDelta(delta, snapshot) {
    if (delta && delta.code_interpreter) {
      if (delta.code_interpreter.input) {
        console.log(delta.code_interpreter.input);
      }
      if (delta.code_interpreter.outputs) {
        console.log("\n\nSalida > ");
        delta.code_interpreter.outputs.forEach(output => {
          if (output.type === "logs") {
            console.log(output.logs);
          }
        });
      }
    }
  }
}

// Función para interactuar con el asistente y obtener respuesta
export async function interactWithAssistant(userMessage) {
  // Crear un hilo de conversación solo si no existe
  if (!threadId) {
    const thread = await openai.chat.createThread({
      messages: [],
    });
    threadId = thread.id;
    console.log("Hilo creado:", threadId);
  }

  const eventHandler = new EventHandler();

  try {
    // Enviar mensaje del usuario al hilo
    await openai.chat.sendMessage({
      threadId: threadId,
      role: 'user',
      content: userMessage,
    });
    console.log("Mensaje enviado:", userMessage);

    // Usar el stream para obtener respuestas en tiempo real
    const stream = openai.chat.stream({
      threadId: threadId,
      eventHandler: eventHandler,
    });

    // Esperar que la respuesta esté lista
    await stream.untilDone();
    
    return "Respuesta completada";  // Aquí puedes devolver la respuesta procesada del asistente si lo deseas

  } catch (error) {
    console.error('Error al interactuar con el asistente:', error);
    throw error; // Lanza el error para que sea manejado en el webhook
  }
}
