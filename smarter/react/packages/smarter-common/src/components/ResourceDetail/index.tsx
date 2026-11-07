export { default } from "./Component";
export type { ResourceDetailProps, ResourceDetailTab } from "./Component";
export {
  asYaml,
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  NoValue,
  prettyJson,
  ResourceMetadataSection,
} from "./DetailFields";
export type {
  DetailFieldProps,
  DetailOverviewProps,
  DetailSectionProps,
  DetailTone,
  DetailValueType,
  ResourceMetadata,
  ResourceMetadataSectionProps,
} from "./DetailFields";
export { CodeBlock, highlightJson, plainLines } from "./code";
export type { CodeBlockProps, CodeLine } from "./code";
export { highlightYaml } from "./yaml";
export { fetchResourceDetail } from "./api";
export type { ResourceDetailData } from "./api";
