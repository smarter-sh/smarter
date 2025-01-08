import { DEBUG_COOKIE_EXPIRATION, DEBUG_COOKIE_NAME, SESSION_COOKIE_NAME, SESSION_COOKIE_EXPIRATION } from "./constants.js";


export function getCookie(name, debugMode = false) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
              if (debugMode) {
                console.log('getCookie(): found ', cookieValue, 'for cookie', name);
              }
              break;
          }
      }
  }
  if (debugMode && !cookieValue) {
    console.warn('getCookie(): no value found for', name);
  }
  return cookieValue;
}

export function setSessionCookie(session_key, debugMode = false) {

      if (session_key) {
        const expirationDate = new Date();
        expirationDate.setTime(expirationDate.getTime() + SESSION_COOKIE_EXPIRATION);
        const expires = expirationDate.toUTCString();
        const currentPath = window.location.pathname;
        const cookieData = `${SESSION_COOKIE_NAME}=${session_key}; path=${currentPath}; SameSite=Lax; expires=${expires}`;
        document.cookie = cookieData;
        if (debugMode) {
          console.log('setSessionCookie(): ', cookieData, 'now: ', new Date().toUTCString(), 'expiration: ', expirationDate.toUTCString());
        }
      }
      else {
        console.error("config.js: session_key is not defined");
      }

}

export function setDebugCookie(debugMode) {
  debugMode = debugMode || false;
  const expirationDate = new Date();
  expirationDate.setTime(expirationDate.getTime() + DEBUG_COOKIE_EXPIRATION);
  const expires = `expires=${expirationDate.toUTCString()}`;

  document.cookie = `${DEBUG_COOKIE_NAME}=${debugMode}; path=/; SameSite=Lax; ${expires}`;

  if (debugMode) {
    console.log('setDebugCookie(): ', debugMode);
  }
}
