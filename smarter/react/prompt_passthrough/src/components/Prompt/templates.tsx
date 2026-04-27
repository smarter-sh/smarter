import getDefaultModel from "./defaultModels";

const helloWorld = {
  messages: [
    {
      role: "user",
      content: "Hello world",
    },
  ],
};

const messageRoles = {
  temperature: 0.5,
  max_tokens: 1024,
  messages: [
    {
      role: "system",
      content: "You are a helpful assistant.",
    },
    {
      role: "assistant",
      content: "Hello! How can I assist you today?",
    },
    {
      role: "user",
      content: "What is the capital of France?",
    },
  ],
};

const functionCallPrompt = {
  temperature: 0.7,
  max_tokens: 1024,
  messages: [
    {
      role: "user",
      content: "What is the weather like in New York?",
    },
  ],
  functions: [
    {
      name: "getWeather",
      description: "Get the current weather in a given location",
      parameters: {
        type: "object",
        properties: {
          location: {
            type: "string",
            description: "The city and state, e.g. San Francisco, CA",
          },
          unit: {
            type: "string",
            enum: ["celsius", "fahrenheit"],
          },
        },
        required: ["location"],
      },
    },
  ],
};

export default function getPromptTemplate(templateId: string, llmProviderId: string) {
  const defaultModel = getDefaultModel(llmProviderId);
  let template;
    switch (templateId) {
      case "1":
        template = helloWorld;
        break;
      case "2":
        template = messageRoles;
        break;
      case "3":
        template = functionCallPrompt;
        break;
      default:
        template = helloWorld;
    }
    return JSON.stringify({model: defaultModel, ...template}, null, 2);
}
