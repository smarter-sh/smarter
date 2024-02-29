// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.
let element = document.getElementById("react-config");
export const REACT_CONFIG = element ? JSON.parse(element.textContent) : {
  BACKEND_API_URL: "http://127.0.0.1:8000/api/v0"
};

export const BACKEND_API_URL = REACT_CONFIG.BACKEND_API_URL;
export const BACKEND_API_TEST_URL = BACKEND_API_URL;
export const APPLICATIONS = {
  SmarterSandbox: "SmarterSandBox",
  LangchainPassthrough: "LangchainPassthrough",
  OpenaiPassthrough: "OpenaiPassthrough",
};

// FIX NOTE: DELETE ME
export const AWS_API_GATEWAY_KEY = "YOUR_AWS_API_KEY";
export const INFO_URL = "https://smarter.sh";
