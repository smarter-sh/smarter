import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";

/** The note below the web console's title, with the fact of a fixed day so that it doesn't change. */
const meta = {
  title: "DidYouKnow/App",
  component: App,
  args: { date: new Date("2026-10-20T12:00:00Z") },
  decorators: [
    (Story) => (
      <div className="p-6">
        <h1 className="smarter-product-title">The Smarter Project</h1>
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
