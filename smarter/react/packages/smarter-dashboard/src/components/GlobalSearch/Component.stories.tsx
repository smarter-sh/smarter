import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, globalSearchHandler } from "@/mocks/handlers";

import GlobalSearch from "@/components/GlobalSearch/Component";

/** Search every resource by name, description, tag or annotation. */
const meta = {
  title: "Dashboard/GlobalSearch",
  component: GlobalSearch,
  args: { sessionContext, apiUrl: appContext.globalSearchApiUrl },
  parameters: { msw: { handlers: [globalSearchHandler] } },
} satisfies Meta<typeof GlobalSearch>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Results: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByRole("searchbox", { name: "Search every resource" }), "tag:production");
    await expect(await canvas.findByRole("link", { name: "guardrail_1" })).toBeInTheDocument();
  },
};

export const InvalidAnnotation: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByRole("searchbox", { name: "Search every resource" }), "Bad Key=x");
    await expect(await canvas.findByRole("alert")).toHaveTextContent("invalid name segment");
  },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByRole("searchbox", { name: "Search every resource" }), "support");
    await expect(await canvas.findByRole("alert")).toHaveTextContent("Search failed");
  },
};
