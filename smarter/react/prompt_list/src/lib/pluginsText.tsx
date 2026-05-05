import type { Chatbot } from "@/lib/Types";

export const pluginsText = (chatbot: Chatbot) => {
  if (!chatbot.tags || chatbot.tags.length === 0) {
    return "-";
  }
  return chatbot.tags.join(", ");
};
