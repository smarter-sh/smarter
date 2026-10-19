import type { Meta, StoryObj } from "@storybook/react-vite";

import { HighlightedYaml } from "@/components/ManifestSection";
import Terminal from "@/components/Terminal";
import { MANIFEST_YAML } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/Terminal",
  component: Terminal,
  args: { title: "bash", code: "smarter deploy llmclient stackademy" },
} satisfies Meta<typeof Terminal>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A command, with its Copy button, which src/components/Terminal.test.tsx tests with a clipboard. */
export const Command: Story = {};

/** The manifest, highlighted, in a tall console that scrolls. */
export const Manifest: Story = {
  args: {
    title: "stackademy.yaml",
    code: MANIFEST_YAML,
    tall: true,
    children: <HighlightedYaml text={MANIFEST_YAML} />,
  },
};
