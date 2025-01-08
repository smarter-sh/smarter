// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.
import { getCookie, setSessionCookie, setDebugCookie } from "./cookies.js";
import { CSRF_COOKIE_NAME, DEBUG_COOKIE_NAME, SESSION_COOKIE_NAME} from "./constants.js"

export async function fetchConfig() {
  /*
  Fetch the chat configuration from the backend server. This is a POST request with the
  session key as the payload. The server will return the configuration
  as a JSON object.

  See class ChatConfigView(View, AccountMixin) in smarter/smarter/apps/chatapp/views.py.
  Things to note:
  - The session key is used to identify the user, the chatbot,
    and the chat history.
  - The session key is stored in a cookie that is specific to the path. Thus,
    each chatbot has its own session key.
  - The CSRF token is stored in a cookie and is managed by Django.
  - debug_mode is a boolean that is also stored in a cookie, managed by Django
    based on a Waffle switch 'reactapp_debug_mode'
  */
  const session_key = getCookie(SESSION_COOKIE_NAME);
  const csrftoken = getCookie(CSRF_COOKIE_NAME);
  const debug_mode = getCookie(DEBUG_COOKIE_NAME) || false;

  const headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "X-CSRFToken": csrftoken,
    "Origin": window.location.origin,
  };
  const body = {
    SESSION_COOKIE_NAME: session_key
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
    if (session_key) {
      thisURL.searchParams.append(SESSION_COOKIE_NAME, session_key);
    }
    let configURL = thisURL.toString();

    if (debug_mode) {
      console.log('fetchConfig() - init: ', init);
      console.log('fetchConfig() - configURL: ', configURL);
    }

    const response = await fetch(configURL, init);
    const response_json = await response.json();    // Convert the ReadableStream to a JSON object

    if (debug_mode) {
      console.log('fetchConfig() - response_json: ', response_json);
    }
    if (response.ok) {
      return response_json.data;
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
    setSessionCookie(config.session_key, config.debug_mode);
    setDebugCookie(config.debug_mode);
    return config;
}
