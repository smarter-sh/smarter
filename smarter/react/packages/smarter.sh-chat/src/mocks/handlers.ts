/** MSW request handlers for the Smarter api. See storybook/preview.ts and test/server.ts in the workspace. */
import { delay, http, HttpResponse } from "msw";

import { VERBOSE_PARAMETER } from "@/lib/api";
import type { ChatConfig } from "@/types";

import {
  CONFIG_URL,
  PROMPT_URL,
  apiErrorResponse,
  config,
  configWithHistory,
  configWithDiagram,
  configWithImages,
  configWithMath,
  configWithStyles,
  leanConfig,
  promptErrorResponse,
  promptEventStream,
  promptResponse,
} from "./fixtures";

const eventStreamHeaders = { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" };

/** The config api, which returns the configuration's diagnostic parts only with ?verbose=true. */
function configHandler(chatConfig: ChatConfig) {
  return http.post(CONFIG_URL, ({ request }) => {
    const verbose = new URL(request.url).searchParams.get(VERBOSE_PARAMETER) === "true";
    return HttpResponse.json({ data: verbose ? chatConfig : leanConfig(chatConfig), api: "smarter.sh/v1" });
  });
}

/** A new chat session, whose prompts succeed. */
export const chatHandlers = [configHandler(config), http.post(PROMPT_URL, () => HttpResponse.json(promptResponse()))];

/** A chat session in progress. */
export const historyHandlers = [
  configHandler(configWithHistory),
  http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())),
];

/** The LLM provider rejects the prompt. */
export const promptErrorHandlers = [
  configHandler(config),
  http.post(PROMPT_URL, () => HttpResponse.json(promptErrorResponse(), { status: 401 })),
];

/** The configuration never arrives. */
export const loadingHandlers = [
  http.post(CONFIG_URL, async () => {
    await delay("infinite");
    return HttpResponse.json({});
  }),
];

/** The LLMClient doesn't exist, or the user may not use it. */
export const configErrorHandlers = [
  http.post(CONFIG_URL, () => HttpResponse.json(apiErrorResponse(), { status: 404 })),
];

/** A chat session whose assistant replied with markdown images. */
export const imageHandlers = [
  configHandler(configWithImages),
  http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())),
];

/** A chat session with an LLMClient that has styles: a logo, avatars, a background image, a font and colors. */
export const stylesHandlers = [
  configHandler(configWithStyles),
  http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())),
];

/** A chat session whose assistant replied with a mermaid diagram. */
export const diagramHandlers = [
  configHandler(configWithDiagram),
  http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())),
];

/** A chat session whose assistant replied with math, in LaTeX. */
export const mathHandlers = [
  configHandler(configWithMath),
  http.post(PROMPT_URL, () => HttpResponse.json(promptResponse())),
];

/**
 * The prompt api streams the prompt's progress, a step every second, and then its result. The
 * log stream sends the recent logs, and then a new one.
 */
export const streamingHandlers = [
  configHandler(config),
  http.post(PROMPT_URL, () => {
    const encoder = new TextEncoder();
    const frames = promptEventStream().split(/(?<=\n\n)/);
    const stream = new ReadableStream({
      async start(controller) {
        for (const frame of frames) {
          controller.enqueue(encoder.encode(frame));
          await delay(frame.startsWith("event: progress") ? 1000 : 0);
        }
        controller.close();
      },
    });
    return new HttpResponse(stream, { headers: eventStreamHeaders });
  }),
];
