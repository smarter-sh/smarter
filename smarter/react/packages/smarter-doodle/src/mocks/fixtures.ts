/**
 * Example data for this package's stories and tests: the root element's attributes, and what the
 * doodle api returns. See templates/react/doodle.html and smarter.apps.doodle.api.v1.views.
 */
import type { AppContext, DoodleApiResponse } from "@/lib/Types";

/** The Django dev server's static files, which Storybook's stylesheets also come from. */
const STATIC_URL = "http://localhost:9357/static/";

export const appContext: AppContext = {
  apiUrl: "/api/v1/doodles/today/",
  baseImageUrl: `${STATIC_URL}doodle/base.svg`,
  homeUrl: "/",
  logoUrl: `${STATIC_URL}images/logo/smarter-crop.png`,
  productName: "The Smarter Project",
  productDescription: "An open source, no-code AI authoring platform designed for instructional use.",
  projectUrl: "https://smarter.sh",
};

export const diwali: DoodleApiResponse = {
  date: "2026-11-08",
  region: "south-asia",
  theme: "diwali",
  title: "Diwali",
  caption: "Happy Diwali!",
  altText: "Glowing diyas line the ground below a Smarter LLMClient, under a string of colorful lights.",
  linkUrl: "https://en.wikipedia.org/wiki/Diwali",
  imageUrl: `${STATIC_URL}doodle/base.svg`,
  isDefault: false,
  animated: true,
  showCaption: true,
};

export const quietDay: DoodleApiResponse = {
  ...diwali,
  date: "2026-11-03",
  region: "global",
  theme: "default",
  title: "The Smarter Project",
  caption: "",
  altText: "A Smarter LLMClient's chat window, with the plugin, guardrail, vectorstore and secret that it uses.",
  linkUrl: "",
  isDefault: true,
  showCaption: false,
};
