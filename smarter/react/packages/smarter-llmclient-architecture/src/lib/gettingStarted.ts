/**
 * What the tab suggests beneath the tree, for an LLMClient that has no Guardrail, no tools or no styles, and the
 * manifest excerpts that it suggests, to copy into the LLMClient's manifest. The names in the excerpts are
 * resources that every platform has: the built-in Guardrails, the sample plugins, the example MCPClients and the
 * official Extensions, which `manage.py initialize_platform` adds.
 */
import { PLUGIN_KINDS } from "./kinds";
import type { SAMDependencyTreeNode } from "./types";

/** The kinds that give an LLMClient tools: its plugins, Extensions and MCPClients. */
export const TOOL_KINDS = [...PLUGIN_KINDS, "Extension", "MCPClient"];

/** Whether the LLMClient itself uses a resource of one of the kinds, readable or not. */
const usesKind = (tree: SAMDependencyTreeNode, kinds: readonly string[]) =>
  tree.children.some((child) => kinds.includes(child.kind));

/** Whether the LLMClient has a Guardrail. */
export const hasGuardrail = (tree: SAMDependencyTreeNode) => usesKind(tree, ["Guardrail"]);

/** Whether the LLMClient has tools: a plugin, an Extension or an MCPClient. */
export const hasTools = (tree: SAMDependencyTreeNode) => usesKind(tree, TOOL_KINDS);

/**
 * A manifest excerpt: the lines that the user adds, and above them, the lines of the manifest that they go
 * beneath, which the tab shows dimmed, and doesn't copy.
 */
export interface ManifestSnippet {
  /** The lines that are already in the manifest, e.g. "spec:". */
  context: string;
  /** The lines to add, indented as they are in the manifest. */
  code: string;
}

/** Two built-in Guardrails that need no LLM: one redacts personal data, the other blocks prompt injection. */
export const GUARDRAIL_SNIPPET: ManifestSnippet = {
  context: "spec:",
  code: "  guardrails:\n    - pii_redaction_input\n    - prompt_injection_keyword_input",
};

/** A sample static plugin, which needs no Connection or Secret. */
export const PLUGIN_SNIPPET: ManifestSnippet = {
  context: "spec:",
  code: "  plugins:\n    - everlasting_gobstopper",
};

/** An official Extension. */
export const EXTENSION_SNIPPET: ManifestSnippet = {
  context: "spec:",
  code: "  extensions:\n    - calculator",
};

/** An example MCPClient whose server requires no authentication. */
export const MCPCLIENT_SNIPPET: ManifestSnippet = {
  context: "spec:",
  code: "  mcpClients:\n    - deepwiki",
};

/** A logo, a font, and the colors of the header and of the user's messages. */
export const STYLES_SNIPPET: ManifestSnippet = {
  context: "spec:\n  config:\n    prompt:\n      ...",
  code: [
    "    styles:",
    "      appLogoUrl: https://cdn.smarter.sh/images/logo/smarter-crop.png",
    "      googleFont: Inter",
    "      conversationHeader:",
    '        backgroundColor: "#1b1f3b"',
    '        color: "#ffffff"',
    "      outgoingMessage:",
    '        backgroundColor: "#ff5733"',
    '        color: "#ffffff"',
  ].join("\n"),
};
