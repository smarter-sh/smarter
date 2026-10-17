/**
 * MSW handlers for the terminal: the ticket api, and, for Storybook, a WebSocket with a pretend
 * shell, which echoes what is typed, and answers a few commands. Tests drive the WebSocket with
 * mocks/fakes.ts instead.
 */
import { http, HttpResponse, ws } from "msw";

import { TICKET_URL, prompt, sessionMessage, ticket } from "./fixtures";

const encoder = new TextEncoder();

const answers: Record<string, string> = {
  hostname: "smarter-app-7d9f8c6b5-x2kqp",
  whoami: "smarter_user",
  pwd: "/home/smarter_user",
  ls: "smarter  venv",
};

export const ticketHandlers = [http.post(TICKET_URL, () => HttpResponse.json(ticket))];

export const ticketRefusedHandlers = [http.post(TICKET_URL, () => new HttpResponse(null, { status: 404 }))];

const terminal = ws.link(/\/ws\/terminal\//);

export const shellHandlers = [
  ...ticketHandlers,
  terminal.addEventListener("connection", ({ client }) => {
    let line = "";
    client.send(JSON.stringify(sessionMessage));
    client.send(encoder.encode(prompt));
    client.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.type !== "input") return;
      for (const key of message.data as string) {
        if (key === "\r") {
          const command = line.trim();
          line = "";
          if (command === "exit") {
            client.send(encoder.encode("\r\nlogout\r\n"));
            client.send(JSON.stringify({ type: "exit", reason: "exited", code: 0 }));
            return;
          }
          const answer = command ? (answers[command] ?? `bash: ${command}: command not found`) : "";
          client.send(encoder.encode(`\r\n${answer ? `${answer}\r\n` : ""}${prompt}`));
        } else if (key === "\x7f") {
          if (line) {
            line = line.slice(0, -1);
            client.send(encoder.encode("\b \b"));
          }
        } else {
          line += key;
          client.send(encoder.encode(key));
        }
      }
    });
  }),
];
