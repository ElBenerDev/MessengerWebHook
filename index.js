import { OpenAI } from 'openai'; // Importa OpenAI de la librería
import readline from 'readline'; // Para la entrada por consola

// Configura el cliente de OpenAI con tu API Key
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // Usar la clave API de entorno
});

const assistantId = "asst_Q3M9vDA4aN89qQNH1tDXhjaE"; // ID del asistente
let threadId = ''; // Almacenaremos el threadId aquí

// Crear un manejador de eventos
class EventHandler {
  onTextCreated(text) {
    console.log(`\nAsistente: ${text}`);
  }

  onTextDelta(delta, snapshot) {
    if (delta.value) process.stdout.write(delta.value); // Imprimir cuando cambia el texto
  }

  onToolCallCreated(toolCall) {
    console.log(`\nAsistente > ${toolCall.type}`);
  }

  onToolCallDelta(delta, snapshot) {
    if (delta.code_interpreter) {
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

// Función para crear un hilo y manejar los mensajes
async function createThread() {
  const thread = await openai.beta.threads.create({});
  threadId = thread.id; // Guardar el ID del hilo
  console.log("Hilo creado:", thread.id);
}

// Función para continuar la conversación
async function continueConversation() {
  while (true) {
    // Leer el mensaje del usuario
    const userMessage = await askQuestion("\nTú: ");
    if (userMessage.toLowerCase() === "salir") {
      console.log("Terminando conversación...");
      break;
    }

    // Enviar mensaje del usuario al hilo
    await openai.beta.threads.messages.create(threadId, {
      role: "user",
      content: userMessage,
    });
    console.log("Mensaje enviado:", userMessage);

    // Procesar la respuesta usando el EventHandler
    const eventHandler = new EventHandler();
    const stream = await openai.beta.threads.runs.stream({
      thread_id: threadId,
      assistant_id: assistantId,
      event_handler: eventHandler,
    });

    // Esperar a que termine el stream
    await stream.untilDone();
  }
}

// Función para hacer preguntas al usuario
function askQuestion(query) {
  return new Promise((resolve) => {
    rl.question(query, resolve);
  });
}

// Crear un hilo y empezar la conversación
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

async function start() {
  await createThread();
  await continueConversation();
}

start();
