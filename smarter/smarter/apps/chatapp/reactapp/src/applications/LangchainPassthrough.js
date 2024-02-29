import {
  BACKEND_API_URL,
  AWS_API_GATEWAY_KEY,
  INFO_URL,
} from "../config";

const SLUG = "langchain";

const OpenaiPassthrough = {
  sidebar_title: "Langchain OpenAI",
  api_url: BACKEND_API_URL + SLUG,
  api_key: AWS_API_GATEWAY_KEY,
  app_name: "Langchain OpenAI",
  assistant_name: "Lance",
  welcome_message: `Hello, I'm Lance, a Langchain-based OpenAI ChatGPT assistant.`,
  example_prompts: [],
  placeholder_text: `say something to Lance`,
  info_url: INFO_URL,
  file_attach_button: false,
  // background_image_url: "/applications/SarcasticChat/SarcasticChat-bg.png",
  // application_logo: "https://www.querium.com/wp-content/uploads/2022/03/cropped-favicon-1-1-192x192.png",
  // uses_openai: true,
  // uses_openai_api: false,
  // uses_langchain: true,
  // uses_memory: true,
};

export default OpenaiPassthrough;
