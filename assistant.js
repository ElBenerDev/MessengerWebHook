import { OpenAI } from 'openai';
import dotenv from 'dotenv';
import readline from 'readline';

// Cargar variables de entorno
dotenv.config();

// Crear cliente de OpenAI con la clave de la API
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,  // La API Key debe estar en .env
});

// Crear un hilo de conversación
let threadId = null;

// Configurar la interfaz de lectura de línea
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Crear un manejador de eventos para manejar la transmisión de respuestas
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

// Función para continuar la conversación
async function continueConversation() {
  // Crear un hilo de conversación
  const thread = await openai.chat.createThread({
    messages: [],
  });
  threadId = thread.id;
  console.log("Hilo creado:", threadId);

  const eventHandler = new EventHandler();

  // Función para escuchar el input del usuario
  rl.on('line', async (input) => {
    if (input.toLowerCase() === 'salir') {
      console.log("Terminando conversación...");
      rl.close();
      return;
    }

    // Enviar el mensaje del usuario al hilo
    await openai.chat.sendMessage({
      threadId: threadId,
      role: 'user',
      content: input,
    });
    console.log("Mensaje enviado:", input);

    // Usar el stream para obtener respuestas en tiempo real
    const stream = openai.chat.stream({
      threadId: threadId,
      eventHandler: eventHandler,
    });

    // Esperar que la respuesta esté lista
    await stream.untilDone();
  });

  console.log("\nTú: ");
}

// Iniciar la conversación continua
continueConversation();
