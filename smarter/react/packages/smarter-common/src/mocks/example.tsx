/**
 * An example object type, with a minimal ListView and CardView, for the stories and tests of the
 * generic TabbedListView. Each list app supplies its own object type, ListView and CardView.
 */
import type { SessionContext, TabbedViewContext, TabKey } from "../lib/Types";

export type Example = { id: number; name: string };

export const API_URL = "/example/react-integration/api/listview/";

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/common",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export const ownedExamples: Example[] = [
  { id: 1, name: "first_example" },
  { id: 2, name: "second_example" },
];
export const sharedExamples: Example[] = [{ id: 3, name: "shared_example" }];

type ListProps = { isLoading: boolean; ghostRows: number; objects: Example[]; onRequery: () => void };

function ExampleListView({ isLoading, ghostRows, objects, onRequery }: ListProps) {
  if (isLoading) return <p>Loading {ghostRows} rows</p>;
  return (
    <ul aria-label="Examples">
      {objects.map((example) => (
        <li key={example.id}>{example.name}</li>
      ))}
      <li>
        <button type="button" onClick={onRequery}>
          Requery
        </button>
      </li>
    </ul>
  );
}

function ExampleCardView({ objects }: { objects: Example[] }) {
  return (
    <div aria-label="Example cards">
      {objects.map((example) => (
        <article key={example.id}>{example.name}</article>
      ))}
    </div>
  );
}

export const exampleContext: TabbedViewContext<Example> = {
  objectType: {} as Example,
  objectTypeName: "example",
  tabs: [
    { key: "owned" as TabKey, label: "Your Examples" },
    { key: "shared" as TabKey, label: "Shared Examples" },
  ],
  ListView: ExampleListView,
  CardView: ExampleCardView,
};
