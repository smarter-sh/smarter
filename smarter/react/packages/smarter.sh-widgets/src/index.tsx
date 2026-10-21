/**
 * @smarter.sh/ui-widgets: the Smarter web console's dashboard widgets that show no account data,
 * for the web console's dashboard (@smarter/dashboard) and for smarter.sh.
 *
 * The widgets are styled for the Keen Bootstrap theme, which the page provides. The library imports
 * the widgets' own stylesheet, so a page's bundler loads it along with them.
 */
export { default as Cli } from "./components/Cli/Component";
export type { CliProps } from "./components/Cli/Component";
export { default as Contribute } from "./components/Contribute/Component";
export { default as DidYouKnow } from "./components/DidYouKnow/Component";
export type { DidYouKnowProps } from "./components/DidYouKnow/Component";
export { default as Extensions } from "./components/Extensions/Component";
export { default as Instructors } from "./components/Instructors/Component";
export type { InstructorsProps } from "./components/Instructors/Component";
export { default as Integrations } from "./components/Integrations/Component";
export type { IntegrationsProps } from "./components/Integrations/Component";
export { default as McpServer } from "./components/McpServer/Component";
export type { McpServerProps } from "./components/McpServer/Component";
export { default as Sdk } from "./components/Sdk/Component";
export type { SdkProps } from "./components/Sdk/Component";
export { default as ResourceTree } from "./components/ResourceTree/Component";
export type { ResourceTreeProps } from "./components/ResourceTree/Component";
export { default as ResourceCard } from "./components/ResourceTree/ResourceCard";
export type { ResourceTreeNode } from "./components/ResourceTree/types";
export { branchIds, childId, countResources, depth, ROOT_ID } from "./components/ResourceTree/tree";
export type { NodeId } from "./components/ResourceTree/tree";
export { kindInfo, PLUGIN_KINDS } from "./components/ResourceTree/kinds";
export type { KindInfo, Tone } from "./components/ResourceTree/kinds";
export { default as SelfHost } from "./components/SelfHost/Component";
export { default as VSCodeExtension } from "./components/VSCodeExtension/Component";
export { default as WhatsNew } from "./components/WhatsNew/Component";
