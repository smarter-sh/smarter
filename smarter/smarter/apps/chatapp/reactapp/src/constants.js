
// Set to true to enable local development mode,
// which will simulate the server-side API calls.
export const REACT_LOCAL_DEV_MODE = false;

// all cookie management
export const DEFAULT_COOKIE_EXPIRATION = 1000 * 60 * 60 * 24 * 1; // 1 day
export const CSRF_COOKIE_NAME = 'csrftoken';
export const DEBUG_COOKIE_NAME = 'debug';
export const DEBUG_COOKIE_EXPIRATION = DEFAULT_COOKIE_EXPIRATION;
export const SESSION_COOKIE_NAME = 'session_key';
export const SESSION_COOKIE_EXPIRATION = DEFAULT_COOKIE_EXPIRATION;
