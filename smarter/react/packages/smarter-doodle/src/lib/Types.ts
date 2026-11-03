/**
 * The doodle of the day, as GET /api/v1/doodles/today/ returns it. See
 * smarter.apps.doodle.contract.models.DoodleApiResponse.
 */
export interface DoodleApiResponse {
  /** The visitor's local date, e.g. 2026-11-08. */
  date: string;
  /** The visitor's region, e.g. south-asia. */
  region: string;
  /** The theme's slug, e.g. diwali, or default. */
  theme: string;
  /** What the doodle celebrates, e.g. Diwali. */
  title: string;
  /** The caption below the artwork, e.g. Happy Diwali! Empty for none. */
  caption: string;
  /** The artwork's description, for screen readers. */
  altText: string;
  /** Where the caption links to. Empty for nowhere. */
  linkUrl: string;
  /** The artwork's url. */
  imageUrl: string;
  /** Whether it is the plain default doodle, which celebrates nothing. */
  isDefault: boolean;
  /**
   * What a Smarter AI application did: "chosen", the Smarter Doodle Editor chose it; "drawn", the
   * Smarter Doodle Artist drew it too. Empty when a person or the calendar chose it.
   */
  aiCredit: "" | "chosen" | "drawn";
  /** Where the AI credit's Learn how links to: how the doodle is chosen and drawn. */
  learnHowUrl: string;
  /** Whether the artwork is animated. */
  animated: boolean;
  /** Whether to show the caption below the artwork. */
  showCaption: boolean;
}

/** What the Django template passes to the app, in the root element's attributes. */
export interface AppContext {
  /** The url of the doodle of the day. */
  apiUrl: string;
  /** The base scene, which the page shows until the doodle of the day arrives. */
  baseImageUrl: string;
  /** Where the logo links to. */
  homeUrl: string;
  logoUrl: string;
  productName: string;
  productDescription: string;
  /** Where Learn more links to. */
  projectUrl: string;
}
