/**
 * An example object type, with a minimal ListView and CardView, for the stories and tests of the
 * generic TabbedListView. Each list app supplies its own object type, ListView and CardView.
 */
import { AnnotationsRow, TagsRow } from "../components/MetadataChips";
import SortableHeader from "../components/SortableHeader";
import type { Filtering, SessionContext, Sorting, TabbedViewContext, TabKey } from "../lib/Types";

export type Example = { id: number; name: string; tags?: string[]; annotations?: Record<string, string> };

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
  { id: 1, name: "first_example", tags: ["red"], annotations: { "example.com/team": "a" } },
  { id: 2, name: "second_example", tags: ["blue"], annotations: { "example.com/team": "b" } },
];
export const sharedExamples: Example[] = [{ id: 3, name: "shared_example" }];

type ListProps = {
  isLoading: boolean;
  ghostRows: number;
  objects: Example[];
  onRequery: () => void;
  sorting?: Sorting;
};

function ExampleListView({ isLoading, ghostRows, objects, onRequery, sorting }: ListProps) {
  const header = (
    <table>
      <thead>
        <tr>
          <SortableHeader column="name" sorting={sorting}>
            Name
          </SortableHeader>
          <SortableHeader column="id" sorting={sorting}>
            Id
          </SortableHeader>
        </tr>
      </thead>
    </table>
  );
  if (isLoading)
    return (
      <>
        {header}
        <p>Loading {ghostRows} rows</p>
      </>
    );
  return (
    <>
      {header}
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
    </>
  );
}

function ExampleCardView({ objects, filtering }: { objects: Example[]; filtering?: Filtering }) {
  return (
    <div aria-label="Example cards">
      {objects.map((example) => (
        <article key={example.id} aria-label={example.name}>
          {example.name}
          <table>
            <tbody>
              <TagsRow tags={example.tags} filtering={filtering} />
              <AnnotationsRow annotations={example.annotations} filtering={filtering} />
            </tbody>
          </table>
        </article>
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
  filters: { even: "Even examples" },
  ListView: ExampleListView,
  CardView: ExampleCardView,
};

/** Another object type, of a tab with its own views: see exampleContextWithOtherTab. */
export type Other = { slug: string; title: string };

export const otherObjects: Other[] = [{ slug: "other", title: "An other object" }];

function OtherListView({ isLoading, objects }: { isLoading: boolean; objects: Other[] }) {
  if (isLoading) return <p>Loading others</p>;
  return (
    <ul aria-label="Others">
      {objects.map((other) => (
        <li key={other.slug}>{other.title}</li>
      ))}
    </ul>
  );
}

function OtherCardView({ objects }: { objects: Other[] }) {
  return (
    <div aria-label="Other cards">
      {objects.map((other) => (
        <article key={other.slug}>{other.title}</article>
      ))}
    </div>
  );
}

/** The example context, with a third, read-only tab of another object type, as the LLMTool list's Extensions tab is. */
export const exampleContextWithOtherTab: TabbedViewContext<Example> = {
  ...exampleContext,
  tabs: [
    ...exampleContext.tabs,
    { key: "others", label: "Others", objectTypeName: "other", ListView: OtherListView, CardView: OtherCardView },
  ],
};
