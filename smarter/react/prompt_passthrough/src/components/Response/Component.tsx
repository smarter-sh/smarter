/**
 * Response Component
 *
 * Renders a formatted HTTP response preview for the prompt passthrough UI.
 * This component currently uses mock response data and a mock HTTP status code
 * to demonstrate how success and failure states appear in the interface.
 *
 * Features:
 * - Displays an HTTP status code in the card header
 * - Applies conditional status styling based on status range (2xx vs non-2xx)
 * - Shows a success or failure emoji indicator
 * - Pretty-prints JSON response payload content for readability
 *
 * Notes:
 * - `http_response_status` and `responseJson` are currently hardcoded placeholders.
 * - In production usage, these values should come from API call state/props.
 */
import "./styles.css";
import SuccessEmoji, {success_style} from "./status_success";
import FailureEmoji, {failure_style} from "./status_failure";

function Response({ apiResponse }: { apiResponse: { status: number; body: any } | null }) {
  const http_response_status = apiResponse?.status ?? 200;
  const responseJson = apiResponse?.body ?? {
    id: "chatcmpl-abc123",
    object: "chat.completion",
    created: 1714243200,
    model: "gpt-4o-mini",
    choices: [
      {
        index: 0,
        message: {
          role: "assistant",
          content: "Hello! How can I assist you today?",
        },
        finish_reason: "stop",
      },
    ],
    usage: {
      prompt_tokens: 12,
      completion_tokens: 9,
      total_tokens: 21,
    },
  };

  const status_style =
    http_response_status >= 200 && http_response_status < 300
      ? success_style
      : failure_style;

  const status_emoji =
    http_response_status >= 200 && http_response_status < 300
      ? <SuccessEmoji />
      : <FailureEmoji />;

  return (
    <div className="col-lg-12">
      <div className="card shadow-sm">
        <div className="card-header d-flex justify-content-center align-items-center">
          <h3 className="mb-0">HTTP Response Body <span style={status_style}>({http_response_status}) {status_emoji}</span></h3>
        </div>
        <div className="card-body">
          <div>
            <pre style={{ margin: 0 }}>
              {JSON.stringify(responseJson, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Response;
