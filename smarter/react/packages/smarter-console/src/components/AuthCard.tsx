/**
 * The frame of the sign-in pages: on the left, the Doodle, the illustration of the day, while the platform's
 * doodle switch is on, or else the logo, name and description; on the right, the page's title and form, and
 * the footer's links while they're switched on. On a phone, the left panel shrinks to the logo, above the
 * form.
 */
import { Doodle, type DoodleContext } from "@smarter/doodle";
import { gettext } from "@smarter/common";
import type { ReactNode } from "react";

import type { ConsoleSession } from "@/contract.gen";
import { DOODLE_API_URL, DOODLE_BASE_IMAGE_URL } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

/** What the Doodle shows, from the session's branding. */
function doodleContext(session: ConsoleSession): DoodleContext {
  const { branding } = session;
  return {
    apiUrl: DOODLE_API_URL,
    baseImageUrl: DOODLE_BASE_IMAGE_URL,
    homeUrl: "/",
    logoUrl: branding.logoUrl,
    productName: branding.productName,
    productDescription: branding.productDescription,
    projectUrl: branding.projectWebsiteUrl,
  };
}

/** The left panel without the doodle: the logo, the name and the description. */
function PlainAside({ session }: { session: ConsoleSession }) {
  const { branding } = session;
  return (
    <>
      <a href="/" className="smarter-doodle-logo">
        <img alt="Logo" src={branding.logoUrl} />
      </a>
      <div className="smarter-doodle-title">{branding.productName}</div>
      <div className="smarter-doodle-description">
        {branding.productDescription}{" "}
        <a href={branding.projectWebsiteUrl} target="_blank" rel="noopener">
          {gettext("Learn more")}
        </a>
      </div>
    </>
  );
}

function FooterLinks({ session }: { session: ConsoleSession }) {
  const { branding } = session;
  return (
    <nav aria-label={gettext("Legal")} className="d-flex justify-content-center fw-semibold fs-base mt-10">
      <a href={branding.legalUrl} className="px-5" target="_blank" rel="noopener">
        {gettext("Legal")}
      </a>
      <a href={branding.marketingSiteUrl} className="px-5" target="_blank" rel="noopener">
        {gettext("Plans")}
      </a>
      <a href={branding.contactUrl} className="px-5" target="_blank" rel="noopener">
        {gettext("Contact Us")}
      </a>
    </nav>
  );
}

export function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  const { session } = useConsoleSession();
  if (!session) return null;
  return (
    <div className="d-flex flex-column flex-lg-row min-vh-100">
      <aside className="d-flex flex-lg-row-fluid w-lg-50 smarter-doodle-aside">
        <div className="smarter-doodle">
          {session.signIn.doodle ? <Doodle appContext={doodleContext(session)} /> : <PlainAside session={session} />}
        </div>
      </aside>
      <main className="d-flex flex-column flex-lg-row-fluid w-lg-50 align-items-center justify-content-center p-10">
        <div className="w-100" style={{ maxWidth: "28rem" }}>
          <h1 className="fs-2 fw-bold text-center mb-8">{title}</h1>
          {children}
          {session.signIn.footerLinks && <FooterLinks session={session} />}
        </div>
      </main>
    </div>
  );
}
