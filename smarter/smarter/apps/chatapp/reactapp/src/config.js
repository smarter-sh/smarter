// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.
import { getCookie } from "./components/chatApp/csrf.js";

export async function fetchConfig() {
  console.log("fetchConfig()");
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
    let thisURL = new URL(window.location.href);
    thisURL.pathname += "config";
    let configURL = thisURL.toString();

    const response = await fetch(configURL, init);
    const status = await response.status;
    const response_json = await response.json();    // Convert the ReadableStream to a JSON object

    console.log("fetchConfig() response: ", response);

    if (response.ok) {
      return response_json;
    } else {
      console.error("getConfig() error", response);
    }
  } catch (error) {
    console.error("getConfig() error", error);
    return;
  }
}

export function setConfig(config) {

    console.log("config: ", config);

    // Application setup
    config.APPLICATIONS = {
      SmarterSandbox: "SmarterSandBox",
      LangchainPassthrough: "LangchainPassthrough",
      OpenaiPassthrough: "OpenaiPassthrough",
    };

    console.log('config.js: BACKEND_API_URL: ', config.chatbot.url_chatbot);
    console.log('config.js: BACKEND_SESSION_KEY: ', config.session_key);
    console.log('config.js: csrf: ', getCookie('csrftoken'));

    return config;
}


// Export the variables
