import type { Meta, StoryObj } from "@storybook/react-vite";

import Instructors from "@/components/Instructors/Component";

/** The Smarter Instructor Guide and Free Course Designs. */
const meta = {
  title: "Dashboard/Instructors",
  component: Instructors,
} satisfies Meta<typeof Instructors>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
