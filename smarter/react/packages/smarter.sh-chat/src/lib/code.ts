/**
 * Code blocks in markdown messages, displayed as GitHub displays them: syntax highlighted, with
 * the language's name and a copy button in a header above the code.
 *
 * Highlighting is by highlight.js, which runs synchronously, as the markdown renderer does, and
 * whose html is spans with "hljs-*" css classes. Their colors are GitHub's dark theme. See
 * styles.css. The copy button works by event delegation, because messages are html strings rather
 * than React elements. See copyCodeBlock, and SmarterChat's onClick.
 */
import hljs from "highlight.js/lib/common";
import dockerfile from "highlight.js/lib/languages/dockerfile";
import nginx from "highlight.js/lib/languages/nginx";
import powershell from "highlight.js/lib/languages/powershell";

import { gettext } from "./i18n";

// the common languages, e.g. python, javascript, typescript, bash, json, yaml, sql, go, rust, java,
// c, c++, c#, html and css, plus a few that LLMs often write and that common leaves out.
hljs.registerLanguage("dockerfile", dockerfile);
hljs.registerLanguage("nginx", nginx);
hljs.registerLanguage("powershell", powershell);

export const CODE_BLOCK_CLASS = "smarter-chat-code";
export const COPY_BUTTON_CLASS = "smarter-chat-code-copy";
// a mermaid code block, which mermaid.ts displays as a diagram.
export const MERMAID_BLOCK_CLASS = "smarter-chat-mermaid";
const MERMAID_LANGUAGE = "mermaid";
const COPIED_DURATION = 2000;

const HTML_ESCAPES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function escape(text: string): string {
  return text.replace(/[&<>"']/g, (character) => HTML_ESCAPES[character]);
}

/**
 * The language of a code block, from its fence's info string, e.g. "python" from
 * "```python title=asgi.py", or "" when it has none.
 */
export function codeLanguage(info: string | undefined): string {
  return (info ?? "").trim().split(/\s+/)[0].toLowerCase();
}

/**
 * A code block's text, without a closing fence that is at the end of its last line rather than on
 * a line of its own, e.g. "  )```", which LLMs sometimes write. Markdown does not close the block
 * there, so the block ends with the message, and the fence would otherwise be displayed as code.
 */
export function stripTrailingFence(text: string): string {
  return text.replace(/(\S)[ \t]*`{3,}[ \t]*$/, "$1");
}

/**
 * Html for a code block's code: highlighted if its language is one that highlight.js knows, by
 * name or alias (e.g. "py", "js", "sh", "yml"), and otherwise escaped, as GitHub does.
 */
export function highlightCode(text: string, language: string): string {
  if (language && hljs.getLanguage(language)) {
    return hljs.highlight(text, { language, ignoreIllegals: true }).value;
  }
  return escape(text);
}

/**
 * Html for a fenced or indented code block: a header with its language and a copy button, and its
 * highlighted code. A mermaid block is also marked, so that it can be displayed as a diagram. See
 * mermaid.ts.
 */
export function codeBlockHtml(text: string, info?: string): string {
  const language = codeLanguage(info);
  const code = stripTrailingFence(text).replace(/\n$/, "");
  const known = !!language && !!hljs.getLanguage(language);
  const codeClass = known ? `hljs language-${escape(language)}` : "hljs";
  const blockClass = language === MERMAID_LANGUAGE ? `${CODE_BLOCK_CLASS} ${MERMAID_BLOCK_CLASS}` : CODE_BLOCK_CLASS;
  return (
    `<div class="${blockClass}">` +
    `<div class="${CODE_BLOCK_CLASS}-header">` +
    `<span class="${CODE_BLOCK_CLASS}-language">${escape(language)}</span>` +
    `<button type="button" class="${COPY_BUTTON_CLASS}" aria-label="${escape(gettext("Copy code"))}">` +
    `${escape(gettext("Copy"))}</button>` +
    `</div>` +
    `<pre><code class="${codeClass}">${highlightCode(code, language)}\n</code></pre>` +
    `</div>`
  );
}

/**
 * Copies a code block's code to the clipboard when its copy button is clicked, and shows that it
 * did on the button for a moment. Clicks on anything else are ignored.
 *
 * :returns: whether the click was on a copy button.
 */
export function copyCodeBlock(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  const button = target.closest<HTMLButtonElement>(`button.${COPY_BUTTON_CLASS}`);
  const code = button?.closest(`.${CODE_BLOCK_CLASS}`)?.querySelector("pre code");
  if (!button || !code) return false;
  const text = (code.textContent ?? "").replace(/\n$/, "");
  navigator.clipboard
    ?.writeText(text)
    .then(() => {
      button.textContent = gettext("Copied!");
      setTimeout(() => {
        button.textContent = gettext("Copy");
      }, COPIED_DURATION);
    })
    .catch(() => undefined);
  return true;
}
