import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";
import { appContext } from "@/mocks/fixtures";
import { diwaliHandler, drawnByAiHandler, failingHandler, quietDayHandler } from "@/mocks/handlers";

/**
 * The sign-in page's left panel. Its layout is the page's stylesheet, so the stories show it on the
 * page's background, with the same classes.
 */
const meta = {
  title: "Doodle/App",
  component: App,
  args: { appContext, timeZone: "Asia/Kolkata" },
  decorators: [
    (Story) => (
      <div style={{ background: "linear-gradient(160deg, #17123b 0%, #2a1c5a 55%, #3a1d4d 100%)", minHeight: "100vh" }}>
        <div className="smarter-doodle" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
          <Story />
        </div>
      </div>
    ),
  ],
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Diwali, in South Asia. */
export const Holiday: Story = { parameters: { msw: { handlers: [diwaliHandler] } } };

/** Revolution Day in Mexico, chosen and drawn by Smarter AI applications: the credit replaces the description. */
export const DrawnByAi: Story = { parameters: { msw: { handlers: [drawnByAiHandler] } } };

/** A day that nothing is due: the base scene, with no caption. */
export const QuietDay: Story = { parameters: { msw: { handlers: [quietDayHandler] } } };

/** The api fails: the base scene. */
export const ApiFails: Story = { parameters: { msw: { handlers: [failingHandler] } } };
