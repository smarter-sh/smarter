import { beforeEach, describe, expect, it, vi } from "vitest";

import { TerminalSession, websocketUrl } from "@/lib/session";
import { FakeWebSocket, installFakes } from "@/mocks/fakes";
import { sessionContext, sessionMessage, sessionInfo } from "@/mocks/fixtures";
import { ticketHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

function handlers() {
  return { onOpen: vi.fn(), onOutput: vi.fn(), onExit: vi.fn() };
}

describe("websocketUrl", () => {
  it("is wss on an https page, with the ticket and the size", () => {
    const url = websocketUrl(
      "/ws/terminal/",
      "t?&",
      80,
      24,
      new URL("https://platform.example.com/x/") as unknown as Location,
    );
    expect(url).toBe("wss://platform.example.com/ws/terminal/?ticket=t%3F%26&cols=80&rows=24");
  });

  it("is ws on an http page", () => {
    const url = websocketUrl("/ws/terminal/", "t", 80, 24, new URL("http://localhost:9357/") as unknown as Location);
    expect(url).toBe("ws://localhost:9357/ws/terminal/?ticket=t&cols=80&rows=24");
  });
});

describe("TerminalSession", () => {
  beforeEach(() => {
    installFakes();
    server.use(...ticketHandlers);
  });

  it("passes on the session, the output, and the exit, once", async () => {
    const h = handlers();
    const session = new TerminalSession(sessionContext, h);
    await session.connect(80, 24);
    const socket = FakeWebSocket.latest();
    socket.open();
    socket.emitJson(sessionMessage);
    expect(h.onOpen).toHaveBeenCalledWith(expect.objectContaining(sessionInfo));
    socket.emitOutput("hi");
    expect(new TextDecoder().decode(h.onOutput.mock.calls[0][0])).toBe("hi");
    socket.emitJson({ type: "exit", reason: "exited", code: 3 });
    expect(h.onExit).toHaveBeenCalledWith("exited", 3);
    // the server then closes the WebSocket, which is not a second exit.
    socket.drop();
    expect(h.onExit).toHaveBeenCalledTimes(1);
    expect(socket.readyState).toBe(FakeWebSocket.CLOSED);
  });

  it("sends nothing until the WebSocket is open", async () => {
    const session = new TerminalSession(sessionContext, handlers());
    await session.connect(80, 24);
    session.sendInput("x");
    expect(FakeWebSocket.latest().sent).toEqual([]);
  });

  it("calls no handler when the browser closes it", async () => {
    const h = handlers();
    const session = new TerminalSession(sessionContext, h);
    await session.connect(80, 24);
    session.close();
    expect(h.onExit).not.toHaveBeenCalled();
    expect(FakeWebSocket.latest().readyState).toBe(FakeWebSocket.CLOSED);
  });
});
