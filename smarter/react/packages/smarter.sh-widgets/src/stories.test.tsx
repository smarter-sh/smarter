/** Render every story in this package as a test. See test/stories.ts in the workspace. */
import { testStories } from "@test/stories";

testStories(import.meta.glob("./**/*.stories.tsx", { eager: true }));
