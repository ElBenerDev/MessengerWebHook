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

async function continueConversation() {
  try {
    const thread = await openai.beta.threads.create({});
    console.log("Hilo creado:", thread.id);

    const eventHandler = new EventHandler();

    console.log("\nTú:");

    rl.on("line", async (userMessage) => {
      if (userMessage.toLowerCase() === "salir") {
        console.log("Terminando conversación...");
        rl.close();
        return;
      }

      const message = await openai.beta.threads.messages.create(thread.id, {
        role: "user",
        content: userMessage,
      });
      console.log("Mensaje enviado:", message);

      const stream = await openai.beta.threads.runs.stream(thread.id, {
        assistant_id: assistantId,
        event_handler: eventHandler,
      });

      await stream.untilDone();
    });
  } catch (error) {
    console.error("Error:", error);
  }
}

async function interactWithAssistant(userMessage) {
  await continueConversation();
}

export { interactWithAssistant };
