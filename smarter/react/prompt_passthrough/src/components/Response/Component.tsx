import "./styles.css";

function Response() {
  const responseJson = {
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1714243200,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I assist you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 9,
    "total_tokens": 21
  }
};

  return (
    <div className="col-lg-12">
      <div className="card shadow-sm">
        <div className="card-header d-flex justify-content-center align-items-center">
          <h3 className="mb-0">LLM Response JSON</h3>
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
