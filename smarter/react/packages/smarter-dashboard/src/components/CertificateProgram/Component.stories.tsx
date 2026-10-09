import type { Meta, StoryObj } from "@storybook/react-vite";

import CertificateProgram from "@/components/CertificateProgram/Component";

/** The Smarter certificate program. */
const meta = {
  title: "Dashboard/CertificateProgram",
  component: CertificateProgram,
} satisfies Meta<typeof CertificateProgram>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
