import {REACT_CONFIG} from "../config";

let APP = REACT_CONFIG.APP;
let BACKEND = REACT_CONFIG.BACKEND;

console.log('REACT_CONFIG:', REACT_CONFIG);
console.log('APP:', APP);
console.log('BACKEND:', BACKEND);
console.log('API_URL:', BACKEND.API_URL);

const SmarterSandbox = {
  sidebar_title: APP.NAME,
  api_url: BACKEND.API_URL,
  api_key: null,
  app_name: APP.NAME,
  assistant_name: APP.ASSISTANT,
  system_role: "You are a helpful assistant.",
  welcome_message: APP.WELCOME_MESSAGE,
  example_prompts: APP.EXAMPLE_PROMPTS,
  placeholder_text: APP.PLACEHOLDER,
  info_url: APP.INFO_URL,
  file_attach_button: APP.FILE_ATTACHMENT_BUTTON,
  // background_image_url: APP.BACKGROUND_IMAGE_URL,
  // application_logo: APP.LOGO_URL,
};
console.log('SmarterSandbox:', SmarterSandbox);
export default SmarterSandbox;
