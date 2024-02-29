// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.
export const REACT_CONFIG = JSON.parse(document.getElementById("react-config").textContent);
export const BACKEND_API_URL = REACT_CONFIG.BACKEND_API_URL;
export const BACKEND_API_TEST_URL = REACT_CONFIG.BACKEND_API_URL;

// FIX NOTE: DELETE ME
export const AWS_API_GATEWAY_KEY = "YOUR_AWS_API_KEY";
export const OPENAI_EXAMPLES_URL = "https://smarter.sh";
export const APPLICATIONS = {
  SarcasticChat: "SarcasticChat",
};
