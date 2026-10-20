import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import Tour, { type TourProps } from "@/components/Tour/Component";

/** A page with two parts for the tour to point to, like the workbench's chat and Console. */
function TourOfAPage(props: TourProps) {
  const [ready, setReady] = useState(false);
  return (
    <div className="d-flex gap-5 p-10" style={{ height: 400 }} ref={() => setReady(true)}>
      <div id="story-chat" className="card flex-grow-1 p-5">
        Chat
      </div>
      <div id="story-console" className="card flex-grow-1 p-5">
        Console
      </div>
      {ready && <Tour {...props} />}
    </div>
  );
}

/** A guided tour of a page, step by step. */
const meta = {
  title: "Onboarding/Tour",
  component: TourOfAPage,
  args: {
    steps: [
      { title: "Welcome to the workbench", text: "This short tour shows you around." },
      { target: "#story-chat", title: "The chat", text: "Talk to the LLMClient here." },
      { target: "#story-console", title: "The Console", text: "See how it works behind the scenes." },
    ],
    onFinish: fn(),
  },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof TourOfAPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
