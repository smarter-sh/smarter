import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";

import DidYouKnow from "@/components/DidYouKnow/Component";
import { didYouKnowFacts } from "@/lib/facts";

/** The unstyled Did you know? note. Its consumers, the welcome dialog and the title bar, style it. */
const meta = {
  title: "DidYouKnow/DidYouKnow",
  component: DidYouKnow,
  args: { fact: didYouKnowFacts()[0] },
} satisfies Meta<typeof DidYouKnow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithALink: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole("link", { name: "Follow Smarter on GitHub" })).toBeInTheDocument();
  },
};

export const WithoutALink: Story = {
  args: { fact: didYouKnowFacts().find((fact) => !fact.link) ?? didYouKnowFacts()[0] },
};
