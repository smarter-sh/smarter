// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.

export async function getConfig() {

  const headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": window.location.origin,
  };
  const init = {
    method: "GET",
    mode: "cors",
    headers: headers,
  };

  try {
    let configURL = window.location.origin + "/config/";
    const response = await fetch(configURL, init);
    const status = await response.status;
    const response_json = await response.json();    // Convert the ReadableStream to a JSON object
    const response_body = await response_json.body; // ditto

    console.log("getConfig()", status, response_json);

    if (response.ok) {
      return JSON.parse(response_body);
    } else {
      console.log("getConfig() error", status, response.statusText, response_body.message);
      console.error(errTitle, errMessage);
    }
  } catch (error) {
    console.error("getConfig() error", error);
    return;
  }
}
getConfig();

// Application setup
export const APPLICATIONS = {
  SmarterSandbox: "SmarterSandBox",
  LangchainPassthrough: "LangchainPassthrough",
  OpenaiPassthrough: "OpenaiPassthrough",
};

// TODO: This is a hack to get the backend API URL into the frontend.
// we should refactor this to use /chatapp/<name>/config/
// which *should* equate to window.location.origin + "/config/"
let element = document.getElementById("react-config");
export const REACT_CONFIG = element ? JSON.parse(element.textContent) : {
  BACKEND_API_URL: "http://localhost:8000/api/v0/"
};
import { getCookie } from "./components/chatApp/csrf";


// Django Context Integrations
export const BACKEND_BASE_URL = REACT_CONFIG ? REACT_CONFIG.BACKEND.BASE_URL : "http://localhost:8000/";
export const BACKEND_API_URL = REACT_CONFIG ? REACT_CONFIG.BACKEND.API_URL : "http://localhost:8000/api/v0/";
export const BACKEND_CHAT_ID = REACT_CONFIG ? REACT_CONFIG.CHAT.ID : null;
export const BACKEND_CHAT_HISTORY = REACT_CONFIG ? REACT_CONFIG.CHAT.HISTORY : [];
export const BACKEND_CHAT_MOST_RECENT_RESPONSE = REACT_CONFIG ? REACT_CONFIG.CHAT.MOST_RECENT_RESPONSE : null;

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

console.log('config.js: BACKEND_API_URL: ', BACKEND_API_URL);
console.log('config.js: csrf: ', getCookie('csrftoken'));
