import OpenAI from "openai";
import readline from "readline";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

const assistantId = "asst_Q3M9vDA4aN89qQNH1tDXhjaE";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

class EventHandler {
  onTextCreated(text) {
    console.log(`\nAsistente: ${text}`);
  }

  onTextDelta(delta, snapshot) {
    if (delta.value) process.stdout.write(delta.value);
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
        delta.code_interpreter.outputs.forEach((output) => {
          if (output.type === "logs") {
            console.log(output.logs);
          }
        });
      }
    }
  }
}

async function continueConversation(userMessage) {
  try {
    // Crear un hilo para la conversación
    const thread = await openai.beta.threads.create({});
    console.log("Hilo creado:", thread.id);

    // Enviar el mensaje del usuario al hilo
    console.log("\nEnviando mensaje del usuario al hilo...");
    const message = await openai.beta.threads.messages.create(thread.id, {
      role: "user",
      content: userMessage,
    });
    console.log("Mensaje enviado al hilo:", message);

    // Obtener la respuesta del asistente sin flujo, solo la respuesta directa
    const assistantResponse = await openai.beta.threads.messages.create(thread.id, {
      role: "assistant",
      content: "respond",  // Esto es solo un ejemplo, dependiendo de la API
    });

    console.log("Respuesta del asistente:", assistantResponse);

    return assistantResponse;
  } catch (error) {
    console.error("Error en la conversación:", error);
  }
}

async function interactWithAssistant(userMessage) {
  console.log("Iniciando conversación con el asistente...");
  const assistantResponse = await continueConversation(userMessage);
  console.log("Conversación completada. Respuesta del asistente:", assistantResponse);
  return assistantResponse;
}

export { interactWithAssistant };
