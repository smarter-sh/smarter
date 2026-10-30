import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a Tool Plugin's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "LLMTool List/DetailView",
  component: DetailView,
  args: {
    sessionContext,
    object: ownedObjects[0],
    onRequery: () => {},
  },
  parameters: { msw: { handlers: actionHandlers } },
} satisfies Meta<typeof DetailView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** A SQL plugin that is always offered, and is not ready. */
export const Sql: Story = {
  args: {
    object: makeObject(9, {
      name: "course_catalog",
      kind: "SqlPlugin",
      pluginClass: "sql",
      ready: false,
      selector: { directive: "always", searchTerms: null },
      staticData: null,
      sqlData: {
        connection: "example_sql_connection",
        description: "Looks up courses by their title.",
        parameters: {
          type: "object",
          required: ["title"],
          properties: { title: { type: "string", description: "The course's title." } },
          additionalProperties: false,
        },
        sqlQuery: "SELECT * FROM courses WHERE title LIKE '%{title}%'",
        testValues: [{ name: "title", value: "python" }],
        limit: 10,
      },
    }),
  },
};

/** An API plugin. */
export const Api: Story = {
  args: {
    object: makeObject(10, {
      name: "weather_api",
      kind: "ApiPlugin",
      pluginClass: "api",
      staticData: null,
      apiData: {
        connection: "example_api_connection",
        method: "GET",
        endpoint: "/forecast/",
        urlParams: [{ key: "city", value: "{city}" }],
        limit: 5,
      },
    }),
  },
};
