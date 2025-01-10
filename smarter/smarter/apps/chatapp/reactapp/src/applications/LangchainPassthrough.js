export const getLangchainPassthrough = (config) => {
  let APP = config.REACT_CONFIG.APP;
  let BACKEND = config.REACT_CONFIG.BACKEND;

  return {
    sidebar_title: "Langchain OpenAI",
    api_url: BACKEND.API_URL_url,
    api_key: null,
    app_name: "Langchain OpenAI",
    assistant_name: "Lance",
    system_role: "You are a helpful assistant.",
    welcome_message: `Hello, I'm Lance, a Langchain-based OpenAI ChatGPT assistant.`,
    example_prompts: [],
    placeholder_text: `say something to Lance`,
    info_url: APP.INFO_URL,
    file_attach_button: false,
    provider: "langchain",
    // background_image_url: "/applications/SarcasticChat/SarcasticChat-bg.png",
    // application_logo: "https://www.querium.com/wp-content/uploads/2022/03/cropped-favicon-1-1-192x192.png",
    // uses_openai: true,
    // uses_openai_api: false,
    // uses_langchain: true,
    // uses_memory: true,
    config: config,
  };
};
