/** The console, signed in and not, with its session answered by MSW. */
import type { Meta, StoryObj } from "@storybook/react-vite";
import { createMemoryRouter } from "react-router";

import App from "@/App";
import { sessionErrorHandler, userSessionHandler, visitorSessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

function ConsoleAt({ path }: { path: string }) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return <App router={router} />;
}

const meta = {
  title: "Console/App",
  component: ConsoleAt,
  args: { path: "/" },
  parameters: { msw: { handlers: [userSessionHandler] } },
} satisfies Meta<typeof ConsoleAt>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SignedIn: Story = {};

export const Visitor: Story = {
  parameters: { msw: { handlers: [visitorSessionHandler] } },
};

export const ServerUnreachable: Story = {
  parameters: { msw: { handlers: [sessionErrorHandler] } },
};

export const PageNotFound: Story = {
  args: { path: "/no-such-page/" },
};
