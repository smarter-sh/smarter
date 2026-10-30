/**
 * MetadataChips React Components
 *
 * Show a resource's tags and annotations as chips. In a list that can be narrowed by them (see
 * Filtering), each chip is a button: a tag narrows the list to the resources with that tag, and an
 * annotation narrows it to those with the same key and value. A chip that already narrows the list
 * is shown as pressed.
 *
 * Exports:
 * - TagChips, AnnotationChips: the chips.
 * - TagsRow, AnnotationsRow: a row of a card view's details table, labeled "Tags" or "Annotations".
 * - annotationRequirement: the annotation selector requirement that an annotation chip adds.
 *
 * Usage:
 * <TagsRow tags={guardrail.tags} filtering={filtering} />
 * <AnnotationsRow annotations={guardrail.annotations} filtering={filtering} />
 */
import type { ReactNode } from "react";

import type { Annotations, Filtering, Tags } from "../../lib/Types";
import { gettext, interpolate } from "../../lib/i18n";

/** The longest annotation value that a chip shows. Its title shows all of it. */
export const MAX_CHIP_VALUE_LENGTH = 40;

/** The annotation selector requirement that matches an annotation's key and value, e.g. "acme.com/crm-id=A-1". */
export function annotationRequirement(key: string, value: string): string {
  return `${key}=${value}`;
}

function shorten(value: string): string {
  const oneLine = value.replace(/\s+/g, " ").trim();
  return oneLine.length > MAX_CHIP_VALUE_LENGTH ? `${oneLine.slice(0, MAX_CHIP_VALUE_LENGTH - 1)}…` : oneLine;
}

interface ChipProps {
  label: string;
  title: string;
  pressed: boolean;
  onClick?: () => void;
}

/** One chip: a button when it can narrow the list, and text otherwise. */
function Chip({ label, title, pressed, onClick }: ChipProps) {
  const className = `badge ${pressed ? "badge-primary" : "badge-light-primary"} fw-semibold text-break text-start`;
  if (!onClick) {
    return (
      <li className={className} title={title}>
        {label}
      </li>
    );
  }
  return (
    <li>
      <button
        type="button"
        className={`${className} border-0`}
        title={title}
        aria-pressed={pressed}
        disabled={pressed}
        onClick={onClick}
      >
        {label}
      </button>
    </li>
  );
}

interface TagChipsProps {
  tags: Tags | undefined;
  filtering?: Filtering;
}

/** A resource's tags, as chips that narrow the list to the resources with the tag. */
export function TagChips({ tags, filtering }: TagChipsProps) {
  if (!tags?.length) return <span className="text-muted">{gettext("No value")}</span>;
  return (
    <ul className="list-unstyled d-flex flex-wrap gap-1 m-0" aria-label={gettext("Tags")}>
      {tags.map((tag) => (
        <Chip
          key={tag}
          label={tag}
          title={
            filtering
              ? // Translators: tag is a resource's tag, e.g. production.
                interpolate(gettext("Show only the resources tagged %(tag)s"), { tag })
              : tag
          }
          pressed={filtering?.tags.includes(tag) ?? false}
          onClick={filtering ? () => filtering.onTag(tag) : undefined}
        />
      ))}
    </ul>
  );
}

interface AnnotationChipsProps {
  annotations: Annotations | undefined;
  filtering?: Filtering;
}

/** A resource's annotations, as "key: value" chips that narrow the list to the resources with the same annotation. */
export function AnnotationChips({ annotations, filtering }: AnnotationChipsProps) {
  const entries = Object.entries(annotations ?? {});
  if (!entries.length) return <span className="text-muted">{gettext("No value")}</span>;
  return (
    <ul className="list-unstyled d-flex flex-wrap gap-1 m-0" aria-label={gettext("Annotations")}>
      {entries.map(([key, value]) => {
        const requirement = annotationRequirement(key, value);
        return (
          <Chip
            key={key}
            label={value ? `${key}: ${shorten(value)}` : key}
            title={
              filtering
                ? // Translators: requirement is an annotation's key and value, e.g. acme.com/crm-id=A-1.
                  interpolate(gettext("Show only the resources annotated %(requirement)s"), { requirement })
                : `${key}: ${value}`
            }
            pressed={filtering?.annotations.includes(requirement) ?? false}
            onClick={filtering ? () => filtering.onAnnotation(requirement) : undefined}
          />
        );
      })}
    </ul>
  );
}

/** A labeled row of a card view's details table. */
function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <tr>
      <td className="w-25">{label}</td>
      <td>{children}</td>
    </tr>
  );
}

/** The "Tags" row of a card view's details table. */
export function TagsRow({ tags, filtering, label }: TagChipsProps & { label?: string }) {
  return (
    <DetailRow label={label ?? gettext("Tags")}>
      <TagChips tags={tags} filtering={filtering} />
    </DetailRow>
  );
}

/** The "Annotations" row of a card view's details table. */
export function AnnotationsRow({ annotations, filtering, label }: AnnotationChipsProps & { label?: string }) {
  return (
    <DetailRow label={label ?? gettext("Annotations")}>
      <AnnotationChips annotations={annotations} filtering={filtering} />
    </DetailRow>
  );
}
