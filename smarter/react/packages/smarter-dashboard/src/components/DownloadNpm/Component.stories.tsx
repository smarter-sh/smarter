import type { Meta, StoryObj } from "@storybook/react-vite";

import DownloadNpm from "@/components/DownloadNpm/Component";

/** The npm package of the Smarter chat component. */
const meta = {
  title: "Dashboard/DownloadNpm",
  component: DownloadNpm,
  args: { apiUrl: "/dashboard/api/npm/" },
} satisfies Meta<typeof DownloadNpm>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
