/******************************************************************************
 * Prompt templates for the Prompt component. The getPromptTemplate
 * function returns a JSON stringified template based on the templateId
 * and defaultModel provided. The templates themselves live in
 * templates.json, which is also read by the backend unit tests
 * (smarter/apps/prompt/api/v1/views/tests/test_passthrough.py) so that
 * every template is tested against every provider. Add new templates
 * there. The function throws an error if templateId or defaultModel are
 * not provided.
 *****************************************************************************/
import templates from "@/components/Prompt/templates.json";

export interface PromptTemplate {
  id: number;
  name: string;
  body: Record<string, unknown>;
}

export const promptTemplates: PromptTemplate[] = templates;

export default function getPromptTemplate(templateId: number, defaultModel: string) {
  if (!templateId) {
    throw new Error("templateId is required to get a prompt template");
  }
  if (!defaultModel) {
    throw new Error("defaultModel is required to get a prompt template");
  }
  const template = promptTemplates.find((t) => t.id === templateId) ?? promptTemplates[0];
  return JSON.stringify({ model: defaultModel, ...template.body }, null, 2);
}
