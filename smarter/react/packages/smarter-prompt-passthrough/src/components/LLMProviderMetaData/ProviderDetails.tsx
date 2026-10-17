import { useId, type ReactNode } from "react";

import type { LLMProvider, LLMProviderUser } from "@/components/LLMProviders";
import { currentLanguage, gettext, interpolate } from "@smarter/common";

const DATE_FORMAT: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" };
const DATE_TIME_FORMAT: Intl.DateTimeFormatOptions = {
  ...DATE_FORMAT,
  hour: "2-digit",
  minute: "2-digit",
  timeZoneName: "short",
};

/** Parses an api timestamp. Its microseconds are trimmed to milliseconds, which every browser parses. */
function parseDate(value: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value.replace(/(\.\d{3})\d+/, "$1"));
  return isNaN(date.getTime()) ? null : date;
}

/** A date in the language of the page, with the full date and time in its tooltip. Nothing without one. */
function DateValue({ value }: { value: string | null }) {
  const date = parseDate(value);
  if (!date) return <None />;
  return (
    <time dateTime={date.toISOString()} title={date.toLocaleString(currentLanguage(), DATE_TIME_FORMAT)}>
      {date.toLocaleDateString(currentLanguage(), DATE_FORMAT)}
    </time>
  );
}

function None() {
  return <span className="text-gray-500">{gettext("None")}</span>;
}

function Code({ value }: { value: string | null }) {
  if (!value) return <None />;
  return <code className="provider-meta-code">{value}</code>;
}

function EmailLink({ email }: { email: string }) {
  return (
    <a href={`mailto:${email}`} className="text-gray-800 text-hover-primary">
      {email}
    </a>
  );
}

/** A user's name, with their email under it. */
function Person({ user }: { user: LLMProviderUser | null }) {
  if (!user) return <None />;
  return (
    <span className="d-flex flex-column">
      <span>{user.username}</span>
      <span className="provider-meta-secondary">
        <EmailLink email={user.email} />
      </span>
    </span>
  );
}

/** An email address, and whether, and when, the provider verified it. */
function VerifiedEmail({ email, verified }: { email: string | null; verified: string | null }) {
  if (!email) return <None />;
  const date = parseDate(verified);
  return (
    <span className="d-flex flex-column">
      <EmailLink email={email} />
      {date ? (
        <span className="provider-meta-secondary text-success">
          <i className="ki-outline ki-verify fs-7 me-1 text-success" aria-hidden="true"></i>
          {interpolate(
            // Translators: when an email address was verified, e.g. "Verified Oct 15, 2026".
            gettext("Verified %(date)s"),
            { date: date.toLocaleDateString(currentLanguage(), DATE_FORMAT) },
          )}
        </span>
      ) : (
        <span className="provider-meta-secondary">{gettext("Not verified")}</span>
      )}
    </span>
  );
}

interface DetailProps {
  label: string;
  children: ReactNode;
}

/** A label and its value. The value is named by its label, for assistive technology. */
function Detail({ label, children }: DetailProps) {
  const id = useId();
  return (
    <div className="provider-meta-detail">
      <dt id={id}>{label}</dt>
      <dd aria-labelledby={id}>{children}</dd>
    </div>
  );
}

interface SectionProps {
  title: string;
  icon: string;
  children: ReactNode;
}

/** One group of details, as a tile with a small uppercase heading. */
function Section({ title, icon, children }: SectionProps) {
  return (
    <section className="provider-meta-section" aria-label={title}>
      <h4 className="provider-meta-label">
        <i className={`ki-outline ${icon} fs-6 me-2`} aria-hidden="true"></i>
        {title}
      </h4>
      <dl className="m-0">{children}</dl>
    </section>
  );
}

/** Tags or annotations, as chips, or "None". */
function Chips({ label, values }: { label: string; values: string[] }) {
  return (
    <div className="provider-meta-chip-row">
      <span className="provider-meta-label">{label}</span>
      {values.length > 0 ? (
        <ul className="provider-meta-chips" aria-label={label}>
          {values.map((value) => (
            <li key={value} className="badge badge-light fw-semibold text-gray-700">
              {value}
            </li>
          ))}
        </ul>
      ) : (
        <None />
      )}
    </div>
  );
}

/** Each annotation, a one-key object, as "key: value". */
function annotationLabels(annotations: LLMProvider["annotations"]): string[] {
  return annotations.flatMap((annotation) =>
    Object.entries(annotation).map(
      ([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`,
    ),
  );
}

interface ProviderDetailsProps {
  provider: LLMProvider;
}

/**
 * The provider's details in four tiles: how Smarter connects to it, who owns it, its terms of service,
 * and whom to contact. The tiles sit side by side on a wide page, and stack on a narrow one. Its tags
 * and annotations follow, as chips.
 */
export default function ProviderDetails({ provider }: ProviderDetailsProps) {
  const apiKey = provider.apiKey;
  return (
    <>
      <div className="provider-meta-sections">
        <Section title={gettext("Connection")} icon="ki-technology-4">
          <Detail label={gettext("Slug")}>
            <Code value={provider.rfc1034CompliantName} />
          </Detail>
          <Detail label={gettext("Base URL")}>
            <Code value={provider.baseUrl} />
          </Detail>
          <Detail label={gettext("Default model")}>
            <Code value={provider.defaultModel} />
          </Detail>
          <Detail label={gettext("Connectivity path")}>
            <Code value={provider.connectivityTestPath} />
          </Detail>
          <Detail label={gettext("API key secret")}>
            {!apiKey && <None />}
            {apiKey && apiKey.manifestUrl && (
              <a href={apiKey.manifestUrl} className="text-gray-800 text-hover-primary">
                <i className="ki-outline ki-key fs-6 me-1" aria-hidden="true"></i>
                {apiKey.name}
              </a>
            )}
            {apiKey && !apiKey.manifestUrl && <Code value={apiKey.name} />}
          </Detail>
        </Section>

        <Section title={gettext("Ownership")} icon="ki-profile-user">
          <Detail label={gettext("Account")}>{provider.userProfile.account.accountNumber}</Detail>
          <Detail label={gettext("Owner")}>
            <Person user={provider.userProfile.user} />
          </Detail>
          <Detail label={gettext("Ownership requested")}>
            {provider.ownershipRequested ? <EmailLink email={provider.ownershipRequested} /> : <None />}
          </Detail>
          <Detail label={gettext("Created")}>
            <DateValue value={provider.createdAt} />
          </Detail>
          <Detail label={gettext("Updated")}>
            <DateValue value={provider.updatedAt} />
          </Detail>
        </Section>

        <Section title={gettext("Terms of service")} icon="ki-shield-tick">
          <Detail label={gettext("Accepted")}>
            {provider.tosAccepted ? (
              <span className="text-success">
                <i className="ki-outline ki-check-circle fs-6 me-1" aria-hidden="true"></i>
                {gettext("Yes")}
              </span>
            ) : (
              <span className="text-danger">
                <i className="ki-outline ki-cross-circle fs-6 me-1" aria-hidden="true"></i>
                {gettext("No")}
              </span>
            )}
          </Detail>
          <Detail label={gettext("Accepted by")}>
            <Person user={provider.tosAcceptedBy} />
          </Detail>
          <Detail label={gettext("Accepted on")}>
            <DateValue value={provider.tosAcceptedAt} />
          </Detail>
        </Section>

        <Section title={gettext("Contact")} icon="ki-sms">
          <Detail label={gettext("Contact email")}>
            <VerifiedEmail email={provider.contactEmail} verified={provider.contactEmailVerified} />
          </Detail>
          <Detail label={gettext("Support email")}>
            <VerifiedEmail email={provider.supportEmail} verified={provider.supportEmailVerified} />
          </Detail>
        </Section>
      </div>

      <div className="provider-meta-footer">
        <Chips label={gettext("Tags")} values={provider.tags} />
        <Chips label={gettext("Annotations")} values={annotationLabels(provider.annotations)} />
      </div>
    </>
  );
}
