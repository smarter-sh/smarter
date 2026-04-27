import Editor from "@monaco-editor/react";
import { useState } from "react";

function Response() {
  const [responseJson, setResponseJson] = useState({
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
  });

  return (
    <>
      <div className="col-lg-6">
        <div className="card shadow-sm">
          <div className="card-header d-flex justify-content-center align-items-center">
            <h3 className="mb-0">Response JSON</h3>
          </div>
          <div className="card-body">
            <Editor
              height="750px"
              defaultLanguage="json"
              theme="vs-dark"
              value={JSON.stringify(responseJson, null, 2)}
              onChange={(value) => setResponseJson(value ? JSON.parse(value) : {})}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                fontFamily: '"Fira Code", "Consolas", "Monaco", monospace',
                fontLigatures: true,
                lineHeight: 22,
                wordWrap: "on",
                formatOnPaste: true,
                formatOnType: true,
                automaticLayout: true,
              }}
            />
          </div>
        </div>
      </div>
    </>
  );
}

export default Response;
