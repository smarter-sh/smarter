import {
  BACKEND_API_URL,
  AWS_API_GATEWAY_KEY,
  INFO_URL,
} from "../config";

const SLUG = "chatapp";

const SmarterSandbox = {
  sidebar_title: "Smarter Sandbox",
  api_url: BACKEND_API_URL + SLUG,
  api_key: AWS_API_GATEWAY_KEY,
  app_name: "Smarter Sandbox",
  assistant_name: "Sam",
  welcome_message: `Hello, I'm Sam, the Smarter sandbox assistant.`,
  example_prompts: [],
  placeholder_text: `say something to Sam`,
  info_url: INFO_URL,
  file_attach_button: false,
  // background_image_url: "/applications/SarcasticChat/SarcasticChat-bg.png",
  // application_logo: "https://www.querium.com/wp-content/uploads/2022/03/cropped-favicon-1-1-192x192.png",
  // uses_openai: true,
  // uses_openai_api: false,
  // uses_langchain: true,
  // uses_memory: true,
};

export default SmarterSandbox;
