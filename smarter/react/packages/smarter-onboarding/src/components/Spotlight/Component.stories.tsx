import { useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import Spotlight, { type SpotlightProps } from "@/components/Spotlight/Component";

/** A link for the spotlight to point to, like the sidebar's LLM Clients link. */
function SpotlightOnALink(props: Omit<SpotlightProps, "target">) {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  return (
    <div className="p-10">
      <a ref={setTarget} href="#llmclients" className="btn btn-light">
        LLM Clients
      </a>
      {target && <Spotlight target={target} {...props} />}
    </div>
  );
}

/** A sparkling ring around one element, and a short note beside it. */
const meta = {
  title: "Onboarding/Spotlight",
  component: SpotlightOnALink,
  args: { text: "Start building your AI masterpiece here.", onDone: fn() },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof SpotlightOnALink>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithATitle: Story = {
  args: { title: "Your LLM Clients" },
};
