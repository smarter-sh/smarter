// API_KEY access is scaffolded, but in point of fact it's not really
// necessary for this application since Terraform also creates an
// AWS API Gateway 'Usage Plan' that limits access to the API.
//
// The API_KEY is only used to demonstrate how you'd set this up in
// the event that you needed it.
export const AWS_API_GATEWAY_KEY = "YOUR_AWS_API_KEY";
export const BACKEND_API_URL =
  "https://api.openai.lawrencemcdaniel.com/examples/";
export const BACKEND_API_TEST_URL =
  "https://api.openai.lawrencemcdaniel.com/tests/";
export const OPENAI_EXAMPLES_URL = "https://platform.openai.com/examples/";
export const APPLICATIONS = {
  SarcasticChat: "SarcasticChat",
};
