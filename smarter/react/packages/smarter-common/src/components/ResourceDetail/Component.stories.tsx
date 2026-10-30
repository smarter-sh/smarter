import type { Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";

import { ExampleDetailView, ownedExamples, sessionContext } from "../../mocks/example";
import { detailHandler } from "../../mocks/handlers";
import ResourceDetail from "./Component";

/**
 * The detail of a resource of a list, which TabbedListView opens when a row is chosen: the list's Details tab,
 * then the resource's manifest, the hierarchy of what it uses, and what uses it.
 */
const meta = {
  title: "Common/ResourceDetail",
  component: ResourceDetail,
  args: {
    sessionContext,
    object: ownedExamples[0],
    objectTypeName: "example",
    DetailView: ExampleDetailView as never,
    onRequery: () => {},
    onClose: () => {},
    onNext: () => {},
    position: { index: 1, count: 2 },
  },
  parameters: { msw: { handlers: [detailHandler()] } },
} satisfies Meta<typeof ResourceDetail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** An object without a detailUrl, e.g. an Extension: the Details tab only. */
export const DetailsOnly: Story = {
  args: { object: { ...ownedExamples[1], detailUrl: null }, position: { index: 2, count: 2 }, onNext: undefined },
};

/** While the next object loads, from another page of the list. */
export const Navigating: Story = {
  args: { isNavigating: true },
};

/** A detail api that fails. */
export const LoadError: Story = {
  parameters: {
    msw: {
      handlers: [
        http.post("/dashboard/api/resource/Example/:locator/", () =>
          HttpResponse.json({ error: "Example not found." }, { status: 404 }),
        ),
      ],
    },
  },
};
