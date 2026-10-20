import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { appContext, welcome } from "@/mocks/fixtures";

import WelcomeDialog from "@/components/WelcomeDialog/Component";
import { didYouKnowFacts } from "@smarter/didyouknow";

/** The welcome dialog's steps, from the greeting to the links of the last one. */
const meta = {
  title: "Welcome/WelcomeDialog",
  component: WelcomeDialog,
  args: {
    firstName: appContext.firstName,
    logoUrl: appContext.logoUrl,
    illustrationsUrl: appContext.illustrationsUrl,
    urls: welcome.urls,
    error: null,
    showAtStartup: true,
    onShowAtStartupChange: fn(),
    onLastStep: fn(),
    onClose: fn(),
    // the first step shows the Did you know? note, so that the stories don't change from run to run.
    didYouKnow: { step: 0, fact: didYouKnowFacts()[0] },
  },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof WelcomeDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithoutAFirstName: Story = {
  args: { firstName: "" },
};

/** Next, seven times, reaches the links. */
export const LastStep: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    for (let step = 0; step < 7; step++) await userEvent.click(canvas.getByRole("button", { name: "Next" }));
    await expect(canvas.getByRole("link", { name: /Try the Get Weather LLMClient/ })).toBeInTheDocument();
    await expect(args.onLastStep).toHaveBeenCalled();
  },
};

export const LoadingLinks: Story = {
  args: { urls: null },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Go to step 8" }));
    await expect(canvas.getByRole("status")).toHaveTextContent("Loading…");
  },
};

export const LinksError: Story = {
  args: { urls: null, error: "Request failed: 503" },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Go to step 8" }));
    await expect(canvas.getByText("Failed to load the links: Request failed: 503")).toBeInTheDocument();
  },
};
