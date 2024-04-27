export const getSmarterSandbox = (config) => {

  return {
    sidebar_title: config.chatbot.app_name,
    api_url: config.chatbot.url_chatbot,
    session_key: config.session_key,
    api_key: null,
    app_name: config.chatbot.app_name,
    assistant_name: config.chatbot.app_assistant,
    system_role: "You are a helpful assistant.",
    welcome_message: config.chatbot.app_welcome_message,
    example_prompts: config.chatbot.app_example_prompts,
    placeholder_text: config.chatbot.app_placeholder,
    info_url: config.chatbot.app_info_url,
    file_attach_button: config.chatbot.app_file_attachment,
    background_image_url: config.chatbot.app_background_image_url,
    application_logo: config.chatbot.app_logo_url,
    history: config.history,
    config: config,
  };
};
