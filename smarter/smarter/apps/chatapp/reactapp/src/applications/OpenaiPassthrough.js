export const getOpenaiPassthrough = (config) => {
  let APP = config.REACT_CONFIG.APP;
  let BACKEND = config.REACT_CONFIG.BACKEND;

  return {
    sidebar_title: "ChatGPT-3.5",
    api_url: BACKEND.API_URL,
    api_key: null,
    app_name: "ChatGPT-3.5",
    assistant_name: "Chester",
    system_role: "You are a helpful assistant.",
    welcome_message: `Hello, I'm Chester, a ChatGPT assistant.`,
    example_prompts: [],
    placeholder_text: `say something to Chester`,
    info_url: null,
    file_attach_button: false,
    // background_image_url: "/applications/SarcasticChat/SarcasticChat-bg.png",
    // application_logo: "https://www.querium.com/wp-content/uploads/2022/03/cropped-favicon-1-1-192x192.png",
    // uses_openai: true,
    // uses_openai_api: false,
    // uses_langchain: true,
    // uses_memory: true,
    config: config,
  };
};
