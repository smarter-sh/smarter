/**
 * An example object type, with a minimal ListView and DetailView, for the stories and tests of the
 * generic TabbedListView. Each list app supplies its own object type, ListView and DetailView.
 */
import { AnnotationChips, TagChips } from "../components/MetadataChips";
import { DetailField, DetailSection, ResourceMetadataSection } from "../components/ResourceDetail/DetailFields";
import SortableHeader from "../components/SortableHeader";
import type { DetailViewBaseProps, Filtering, SessionContext, Sorting, TabbedViewContext, TabKey } from "../lib/Types";

export type Example = {
  id: number;
  name: string;
  description?: string;
  tags?: string[];
  annotations?: Record<string, string>;
  detailUrl?: string | null;
};

/** The url of an example's detail, as a list api's serializer sends it. See mocks/handlers.ts's detailHandler. */
export const exampleDetailUrl = (id: number) => `/dashboard/api/resource/Example/example-r${id}/`;

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
  {
    id: 1,
    name: "first_example",
    description: "The first example.",
    tags: ["red"],
    annotations: { "example.com/team": "a" },
    detailUrl: exampleDetailUrl(1),
  },
  {
    id: 2,
    name: "second_example",
    tags: ["blue"],
    annotations: { "example.com/team": "b" },
    detailUrl: exampleDetailUrl(2),
  },
];
export const sharedExamples: Example[] = [{ id: 3, name: "shared_example" }];

type ListProps = {
  isLoading: boolean;
  ghostRows: number;
  objects: Example[];
  onRequery: () => void;
  sorting?: Sorting;
  filtering?: Filtering;
};

/** A table of examples, one row per example, with its tags and annotations, as a list app's ListView has. */
function ExampleListView({ isLoading, ghostRows, objects, onRequery, sorting, filtering }: ListProps) {
  return (
    <>
      <table aria-label="Examples">
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
        <tbody>
          {isLoading ? (
            <tr className="ghost">
              <td>Loading {ghostRows} rows</td>
            </tr>
          ) : (
            objects.map((example) => (
              <tr key={example.id}>
                <td>{example.name}</td>
                <td>
                  <TagChips tags={example.tags} filtering={filtering} />
                  <AnnotationChips annotations={example.annotations} filtering={filtering} />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
      <button type="button" onClick={onRequery}>
        Requery
      </button>
    </>
  );
}

/** An example's Details tab. */
export function ExampleDetailView({ object, filtering }: DetailViewBaseProps<Example, SessionContext>) {
  return (
    <>
      <DetailSection title="Example">
        <DetailField label="Name" value={object.name} />
        <DetailField label="Description" value={object.description} wide />
      </DetailSection>
      <ResourceMetadataSection resource={object} filtering={filtering} />
    </>
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
  DetailView: ExampleDetailView,
};

/** Another object type, of a tab with its own views: see exampleContextWithOtherTab. */
export type Other = { slug: string; title: string };

export const otherObjects: Other[] = [{ slug: "other", title: "An other object" }];

function OtherListView({ isLoading, objects }: { isLoading: boolean; objects: Other[] }) {
  if (isLoading) return <p>Loading others</p>;
  return (
    <table aria-label="Others">
      <tbody>
        {objects.map((other) => (
          <tr key={other.slug}>
            <td>{other.title}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function OtherDetailView({ object }: DetailViewBaseProps<Other, SessionContext>) {
  return (
    <DetailSection title="Other">
      <DetailField label="Title" value={object.title} />
    </DetailSection>
  );
}

/** The example context, with a third, read-only tab of another object type, as the LLMTool list's Extensions tab is. */
export const exampleContextWithOtherTab: TabbedViewContext<Example> = {
  ...exampleContext,
  tabs: [
    ...exampleContext.tabs,
    { key: "others", label: "Others", objectTypeName: "other", ListView: OtherListView, DetailView: OtherDetailView },
  ],
};
