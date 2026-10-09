import type { Meta, StoryObj } from "@storybook/react-vite";

import { series } from "@/mocks/fixtures";

import BudgetChart from "@/components/BudgetList/BudgetChart";

/** The budget versus actual spending of a resource, per period. */
const meta = {
  title: "Budget List/BudgetChart",
  component: BudgetChart,
  args: { series, unit: "cost", period: "month", periodicLimit: 100, height: 320 },
} satisfies Meta<typeof BudgetChart>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Cost: Story = {};

export const Tokens: Story = {
  args: { unit: "tokens", period: "day", periodicLimit: 100000 },
};
