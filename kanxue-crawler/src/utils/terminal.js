import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

export async function waitForEnter(promptText = "") {
  const rl = readline.createInterface({ input, output });
  try {
    await rl.question(promptText);
  } finally {
    rl.close();
  }
}
