/**
 * The CI badges of the platform's repository: build, test and deploy, on one line.
 *
 * ``repositoryUrl`` comes from the platform's own ``git remote -v``, on whatever host that is.
 * The badges show only when they can: the url must be a safe https url, and a badge whose
 * image fails to load, because the host doesn't serve these badges, the repository is
 * private or has no such workflow, or the host can't be reached, is left out. When no badge can
 * show, a "CI status unknown" message takes their place.
 *
 * :param repositoryUrl: The https url of the platform's repository, from
 *     ``smarter_settings.repository_url``.
 * :type repositoryUrl: str
 *
 * :returns: A JSX element containing the badges, or the message.
 * :rtype: JSX.Element
 */
import { useState } from "react";
import { gettext } from "@smarter/common";

import { repositoryUrl as validRepositoryUrl } from "@/components/ServiceHealth/repository";

/** The workflows whose badges show: [alt text, workflow file]. */
const WORKFLOWS: [string, string][] = [
  [gettext("Build Status"), "build.yml"],
  [gettext("Test Status"), "test.yml"],
  [gettext("Release Status"), "deploy.yml"],
];

interface CIStatusProps {
  repositoryUrl: string;
}

function UnknownStatus() {
  return (
    <div className="service-health-ci-unknown">
      <i className="ki-outline ki-information-5 fs-6 me-1"></i>
      {gettext("CI status unknown")}
    </div>
  );
}

export default function CIStatus({ repositoryUrl }: CIStatusProps) {
  const [failed, setFailed] = useState<ReadonlySet<string>>(new Set());
  const repository = validRepositoryUrl(repositoryUrl);
  const workflows = WORKFLOWS.filter(([, workflow]) => !failed.has(workflow));

  if (!repository || workflows.length === 0) return <UnknownStatus />;

  return (
    <ul className="service-health-badges" aria-label={gettext("Build status")}>
      {workflows.map(([alt, workflow]) => {
        const href = `${repository}/actions/workflows/${workflow}`;
        return (
          <li key={workflow}>
            <a target="_blank" rel="noopener noreferrer" href={href}>
              <img
                alt={alt}
                src={`${href}/badge.svg?branch=main`}
                onError={() => setFailed((previous) => new Set(previous).add(workflow))}
              />
            </a>
          </li>
        );
      })}
    </ul>
  );
}
