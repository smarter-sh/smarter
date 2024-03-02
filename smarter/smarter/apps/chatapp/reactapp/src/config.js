// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.

// Application setup
export const APPLICATIONS = {
  SmarterSandbox: "SmarterSandBox",
  LangchainPassthrough: "LangchainPassthrough",
  OpenaiPassthrough: "OpenaiPassthrough",
};

let element = document.getElementById("react-config");
export const REACT_CONFIG = element ? JSON.parse(element.textContent) : {
  BACKEND_API_URL: "http://127.0.0.1:8000/api/v0/"
};

// Django Context Integrations
export const BACKEND_BASE_URL = REACT_CONFIG.BACKEND_BASE_URL;
export const BACKEND_API_URL = REACT_CONFIG.BACKEND_API_URL;
export const BACKEND_API_TEST_URL = BACKEND_API_URL;
export const BACKEND_CHAT_ID = REACT_CONFIG.BACKEND_CHAT_ID;
export const BACKEND_CHAT_HISTORY = REACT_CONFIG.BACKEND_CHAT_HISTORY;
export const BACKEND_CHAT_MOST_RECENT_RESPONSE = REACT_CONFIG.BACKEND_CHAT_MOST_RECENT_RESPONSE;


// Backend API ai model defaults
export const BACKEND_API_DEFAULT_MODEL = "gpt-3.5-turbo";
export const BACKEND_API_DEFAULT_MODEL_VERSION = "latest";
export const BACKEND_API_DEFAULT_MODEL_ENGINE = "openai";
export const BACKEND_API_DEFAULT_MODEL_TYPE = "ChatCompletion";
export const BACKEND_API_DEFAULT_TEMPERATURE = 0.5;
export const BACKEND_API_DEFAULT_MAX_TOKENS = 256;
export const BACKEND_API_DEFAULT_TOP_P = 1;
export const BACKEND_API_DEFAULT_FREQUENCY_PENALTY = 0.5;
export const BACKEND_API_DEFAULT_PRESENCE_PENALTY = 0.5;
export const BACKEND_API_DEFAULT_STOP_SEQUENCE = "###";

// FIX NOTE: DELETE ME
export const AWS_API_GATEWAY_KEY = "YOUR_AWS_API_KEY";
export const INFO_URL = "https://smarter.sh";
