import OpenAI from "openai";
import readline from "readline";

// Configurar cliente OpenAI con la API key
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY, // La API key debe estar en el archivo .env
});

// Crear ID del asistente
const assistantId = "asst_Q3M9vDA4aN89qQNH1tDXhjaE";

// Crear interfaz para input de usuario en la terminal
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// Clase EventHandler para manejar eventos
class EventHandler {
  // Evento cuando el asistente crea texto
  onTextCreated(text) {
    console.log(`\nAsistente: ${text}`);
  }

  // Evento cuando hay cambios en el texto del asistente
  onTextDelta(delta, snapshot) {
    if (delta.value) process.stdout.write(delta.value);
  }

  // Evento cuando el asistente llama a herramientas
  onToolCallCreated(toolCall) {
    console.log(`\nAsistente > ${toolCall.type}`);
  }

  // Manejo de salidas de herramientas
  onToolCallDelta(delta, snapshot) {
    if (delta.code_interpreter) {
      if (delta.code_interpreter.input) {
        console.log(delta.code_interpreter.input);
      }
      if (delta.code_interpreter.outputs) {
        console.log("\n\nSalida > ");
        delta.code_interpreter.outputs.forEach((output) => {
          if (output.type === "logs") {
            console.log(output.logs);
          }
        });
      }
    }
  }
}

// Función para iniciar conversación continua
async function continueConversation() {
  try {
    // Crear hilo de conversación
    const thread = await openai.beta.threads.create({});
    console.log("Hilo creado:", thread.id);

    const eventHandler = new EventHandler();

    console.log("\nTú:");

    // Leer input del usuario de manera continua
    rl.on("line", async (userMessage) => {
      if (userMessage.toLowerCase() === "salir") {
        console.log("Terminando conversación...");
        rl.close();
        return;
      }

      // Crear mensaje en el hilo
      const message = await openai.beta.threads.messages.create(thread.id, {
        role: "user",
        content: userMessage,
      });
      console.log("Mensaje enviado:", message);

      // Generar respuesta en tiempo real
      const stream = await openai.beta.threads.runs.stream(thread.id, {
        assistant_id: assistantId,
        event_handler: eventHandler,
      });

      // Esperar hasta que la respuesta esté completa
      await stream.untilDone();
    });
  } catch (error) {
    console.error("Error:", error);
  }
}

// Exportar función principal para usar en otros archivos
export { continueConversation };

// Iniciar conversación si este archivo se ejecuta directamente
if (require.main === module) {
  continueConversation();
}
