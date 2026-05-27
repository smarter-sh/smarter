import type { Meta, StoryObj } from "@storybook/react";
import TabbedListView from "./Component";

const meta: Meta<typeof TabbedListView> = {
	title: "PromptList/TabbedListView",
	component: TabbedListView,
	parameters: {
		layout: "fullscreen",
	},
	args: {
		sessionContext: {
			promptListApiUrl: "/prompt-list/api/",
			csrfCookieName: "csrftoken",
			djangoSessionCookieName: "sessionid",
			cookieDomain: "localhost",
		},
	},
};

export default meta;
type Story = StoryObj<typeof TabbedListView>;

export const Default: Story = {
	args: {
		// uses default args above
	},
};

export const WithCustomCookies: Story = {
	args: {
		sessionContext: {
			promptListApiUrl: "/prompt-list/api/",
			csrfCookieName: "customcsrftoken",
			djangoSessionCookieName: "customsessionid",
			cookieDomain: "localhost",
		},
	},
};
