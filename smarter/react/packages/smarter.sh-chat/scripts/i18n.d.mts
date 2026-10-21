/** Types of scripts/i18n.mjs, for src/catalogs.test.ts. */

/** One message that src/ marks for translation, with the files that use it and their translator comments. */
export interface ExtractedMessage {
  context?: string;
  singular: string;
  plural?: string;
  files: string[];
  comments: string[];
}

/** An entry of a .po file. */
export interface PoEntry {
  context?: string;
  msgid: string;
  plural?: string;
  msgstr: string[];
  comments: string[];
  references: string[];
  flags: string[];
}

/** A parsed .po file: its header's fields, and its entries. */
export interface PoFile {
  header: Record<string, string>;
  headerComments?: string[];
  entries: PoEntry[];
}

export const SRC_DIR: string;
export const LOCALE_DIR: string;
export const DOMAIN: string;
export const TEMPLATE_PATH: string;
export const CATALOGS_PATH: string;
export const LANGUAGES: Record<string, { team: string; pluralForms: string }>;
export class ExtractionError extends Error {}
export function sourceFiles(dir?: string): string[];
export function extractFromSource(file: string, sourceText: string): ExtractedMessage[];
export function extractMessages(files?: string[]): ExtractedMessage[];
export function parsePo(text: string): PoFile;
export function formatPo(messages: ExtractedMessage[], language?: string | null, existing?: PoFile): string;
export function pluralRule(pluralForms: string | undefined): string;
export function formatCatalogs(catalogs: Record<string, PoFile>): string;
export function catalogPath(language: string): string;
export function catalogLanguages(): string[];
export function generatedFiles(): Map<string, string>;
