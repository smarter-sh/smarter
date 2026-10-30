/**
 * DetailView React Component
 *
 * The Details tab of a Tool Plugin's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the plugin's description, status and actions, then when it
 * is offered to the LLM (its selector), the prompt that it runs with, the data that its tool returns, and the metadata
 * that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (LLMTool): The Tool Plugin.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={llmtool} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import { formatSql } from "@/lib/sql";
import type { ApiData, LLMTool, LLMToolDetailViewProps, SqlData, StaticData } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** Whether a structured value has anything to show. */
function hasContent(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

/** A structured value as formatted JSON, or the muted dash of a missing one. */
function JsonField({ label, value, help }: { label: string; value: unknown; help?: string }) {
  return (
    <DetailField label={label} help={help} wide>
      <DetailValue value={hasContent(value) ? value : null} type="json" />
    </DetailField>
  );
}

/** The data of a static plugin: what its tool returns, as is, as YAML, as its manifest has it. */
function StaticDataSection({ data }: { data: StaticData }) {
  // the row keeps the manifest's spec.data, whose one key is staticData: show what is inside it.
  const keys = Object.keys(data);
  const value = keys.length === 1 && keys[0] === "staticData" ? data.staticData : data;
  return (
    <DetailSection title={gettext("Static data")} icon="document">
      <DetailField
        label={gettext("Data")}
        wide
        help={gettext("What the tool returns to the LLM, as is, whenever the LLM calls it.")}
      >
        <DetailValue value={hasContent(value) ? value : null} type="yaml" />
      </DetailField>
    </DetailSection>
  );
}

/** The data of a SQL plugin: the query that its tool runs, and its parameters. */
function SqlDataSection({ data }: { data: SqlData }) {
  return (
    <DetailSection title={gettext("SQL query")} icon="data">
      <DetailField
        label={gettext("Connection")}
        value={data.connection}
        type="code"
        help={gettext("The SQL connection that the query runs on.")}
      />
      <DetailField
        label={gettext("Row limit")}
        value={data.limit}
        type="number"
        help={gettext("The most rows that the query returns.")}
      />
      <DetailField label={gettext("Description")} value={data.description} wide />
      <DetailField label={gettext("Query")} wide>
        {data.sqlQuery ? (
          <pre className="smarter-detail-json">{formatSql(data.sqlQuery)}</pre>
        ) : (
          <DetailValue value={null} />
        )}
      </DetailField>
      <JsonField
        label={gettext("Parameters")}
        value={data.parameters}
        help={gettext("The JSON Schema of the parameters that the LLM fills in when it calls the tool.")}
      />
      <JsonField
        label={gettext("Test values")}
        value={data.testValues}
        help={gettext("Example values of the parameters, used to test the query.")}
      />
    </DetailSection>
  );
}

/** The data of an API plugin: the request that its tool sends. */
function ApiDataSection({ data }: { data: ApiData }) {
  const { connection, method, endpoint, limit, ...rest } = data;
  return (
    <DetailSection title={gettext("API request")} icon="data">
      <DetailField
        label={gettext("Connection")}
        value={connection}
        type="code"
        help={gettext("The API connection that the request is sent with.")}
      />
      <DetailField label={gettext("Method")} value={method} type="code" />
      <DetailField label={gettext("Endpoint")} value={endpoint} type="code" />
      <DetailField
        label={gettext("Result limit")}
        value={limit}
        type="number"
        help={gettext("The most results that the request returns.")}
      />
      {Object.entries(rest).map(([key, value]) => (
        <JsonField key={key} label={key} value={value} />
      ))}
    </DetailSection>
  );
}

/** The section of the data that the plugin's tool returns, by its class. */
function DataSection({ llmtool }: { llmtool: LLMTool }) {
  if (llmtool.sqlData) return <SqlDataSection data={llmtool.sqlData} />;
  if (llmtool.apiData) return <ApiDataSection data={llmtool.apiData} />;
  if (llmtool.staticData) return <StaticDataSection data={llmtool.staticData} />;
  return (
    <DetailSection title={gettext("Data")} icon="document">
      <DetailField label={gettext("Data")} wide>
        <DetailValue value={null} />
      </DetailField>
    </DetailSection>
  );
}

function DetailView({ sessionContext, object: llmtool, onRequery, filtering }: LLMToolDetailViewProps) {
  const selector = llmtool.selector;
  const prompt = llmtool.prompt;
  return (
    <>
      <DetailOverview description={llmtool.description}>
        <span
          className={`badge ${llmtool.ready ? "badge-light-success" : "badge-light"} fw-semibold`}
          title={gettext("Whether the plugin is ready to serve requests.")}
        >
          {llmtool.ready ? gettext("Ready") : gettext("Not ready")}
        </span>
        <Toolbar sessionContext={sessionContext} llmtool={llmtool} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Plugin")} icon="technology-2">
        <DetailField label={gettext("Kind")} value={llmtool.kind} type="code" />
        <DetailField
          label={gettext("Class")}
          value={llmtool.pluginClass}
          type="code"
          help={gettext("Which of Smarter's built-in tool patterns the plugin configures, e.g. static, sql or api.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Selector")} icon="filter">
        <DetailField
          label={gettext("Directive")}
          value={selector?.directive}
          type="code"
          help={gettext(
            "When the plugin's tool is offered to the LLM: always, or only when the prompt contains one of its search terms.",
          )}
        />
        <DetailField label={gettext("Search terms")} value={selector?.searchTerms} type="list" wide />
      </DetailSection>

      <DetailSection title={gettext("Prompt")} icon="message-programming">
        <DetailField label={gettext("Provider")} value={prompt?.provider} />
        <DetailField label={gettext("Model")} value={prompt?.model} type="code" />
        <DetailField label={gettext("Temperature")} value={prompt?.temperature} type="number" />
        <DetailField label={gettext("Max tokens")} value={prompt?.maxTokens} type="number" />
        <DetailField
          label={gettext("System role")}
          value={prompt?.systemRole}
          wide
          help={gettext("The system prompt that the LLM is given with the plugin's tool.")}
        />
      </DetailSection>

      <DataSection llmtool={llmtool} />

      <ResourceMetadataSection resource={llmtool} filtering={filtering} />
    </>
  );
}

export default DetailView;
