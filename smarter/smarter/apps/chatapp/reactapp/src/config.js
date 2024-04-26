// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.
import { getCookie } from "./cookies.js";

export async function fetchConfig() {
  const session_key = getCookie('session_key');
  const csrftoken = getCookie('csrftoken');
  const sessionid = getCookie('sessionid');
  const debugMode = getCookie('debug') || false;

  const headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "X-CSRFToken": csrftoken,
    "Origin": window.location.origin,
    "Cookie": `sessionid=${sessionid}`,
  };
  const body = {
    "session_key": session_key
  };
  const init = {
    method: "POST",
    mode: "cors",
    headers: headers,
    body: JSON.stringify(body),
  };

  try {
    let thisURL = new URL(window.location.href);
    thisURL.pathname += "config/";
    let configURL = thisURL.toString();

    if (debugMode) {
      console.log('fetchConfig() - init: ', init);
      console.log('fetchConfig() - configURL: ', configURL);
    }

    const response = await fetch(configURL, init);
    const status = await response.status;
    const response_json = await response.json();    // Convert the ReadableStream to a JSON object

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

// do additional configuration after having fetched
// config json from the server.
export function setConfig(config) {

    // Application setup
    config.APPLICATIONS = {
      SmarterSandbox: "SmarterSandBox",
      LangchainPassthrough: "LangchainPassthrough",
      OpenaiPassthrough: "OpenaiPassthrough",
    };

    // set cookies
    if (config.session_key) {
      document.cookie = `session_key=${config.session_key}; path=/`;
    }
    else {
      console.error("config.js: session_key is not defined");
    }
    document.cookie = `debug=${config.debugMode}; path=/`;

    if (config.debug_mode) {
      console.log('setConfig() - config: ', config);
    }
    return config;
}


// Export the variables
