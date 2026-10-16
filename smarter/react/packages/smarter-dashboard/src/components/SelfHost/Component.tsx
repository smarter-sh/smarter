/**
 * SelfHost dashboard widget.
 *
 * This component renders a promotional card for self-hosting Smarter, as a
 * three-step path from a laptop to production: the Docker Compose Quick Start
 * (smarter-deploy), the official Helm chart for Kubernetes, and the official
 * Terraform modules for AWS (smarter-infrastructure). Each step links to its
 * resource, followed by a link to the installation guide.
 *
 * :returns: A JSX fragment containing the self-host call-to-action widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <SelfHost />
 */
import "@/components/SelfHost/styles.css";
import { gettext, interpolateNodes } from "@smarter/common";

const STEPS = [
  {
    name: "Docker",
    where: gettext("Your laptop"),
    description: gettext("Quick Start with Docker Compose"),
    logo: "/static/images/selfhost/docker.svg",
    href: "https://github.com/smarter-sh/smarter-deploy",
  },
  {
    name: "Kubernetes",
    where: gettext("Your cluster"),
    description: gettext("The official Helm chart"),
    logo: "/static/images/selfhost/kubernetes.svg",
    href: "https://artifacthub.io/packages/helm/project-smarter/smarter",
  },
  {
    name: "Terraform",
    where: gettext("Your AWS cloud"),
    description: gettext("The official Terraform modules"),
    logo: "/static/images/selfhost/terraform.svg",
    href: "https://github.com/smarter-sh/smarter-infrastructure",
  },
];

function SelfHost() {
  return (
    <>
      {/* begin::Engage widget 4 */}
      <section
        id="self-host"
        aria-label={gettext("Self Host")}
        className="card border-transparent h-100 selfhost-card"
        data-bs-theme="light"
      >
        {/* begin::Body */}
        <div className="card-body d-flex flex-column ps-xl-15 h-100">
          {/* begin::Title */}
          <span className="selfhost-eyebrow">{gettext("Self-host Smarter")}</span>
          <div className="fs-2x fw-bold text-white mt-3 mb-2">
            {/* Translators: a headline. %(span)s is its highlighted last words, translated separately. */}
            {interpolateNodes(gettext("Run it %(span)s"), {
              span: (
                <span className="position-relative d-inline-block">
                  {/* Translators: the highlighted words of a headline. %(span)s is their decorative underline, and stays at the end. */}
                  {interpolateNodes(gettext("anywhere%(span)s"), {
                    span: (
                      <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 selfhost-underline"></span>
                    ),
                  })}
                </span>
              ),
            })}
          </div>
          <p className="fs-6 mb-7 selfhost-lede">
            {gettext("The same open source platform, from your laptop to production. No license fees, no seat counts.")}
          </p>
          {/* end::Title */}
          {/* begin::Steps */}
          <ol className="selfhost-steps">
            {STEPS.map((step, index) => (
              <li key={step.name} className="selfhost-step">
                <a href={step.href} target="_blank" className="selfhost-step-link hover-elevate-up">
                  <span className="selfhost-logo">
                    <img src={step.logo} alt="" />
                    <span className="selfhost-number">{index + 1}</span>
                  </span>
                  <span className="selfhost-where">{step.where}</span>
                  <span className="selfhost-name">{step.name}</span>
                  <span className="selfhost-description">{step.description}</span>
                </a>
              </li>
            ))}
          </ol>
          {/* end::Steps */}
          {/* begin::Action */}
          <div className="d-flex flex-wrap align-items-center gap-3 mt-auto pt-7">
            <a
              href="https://docs.smarter.sh/en/latest/smarter-platform/installation.html"
              target="_blank"
              className="btn btn-sm fw-semibold selfhost-btn"
            >
              {gettext("Installation Guide")}
            </a>
            <span className="selfhost-license">{gettext("Open source &middot; AGPL-3.0")}</span>
          </div>
          {/* end::Action */}
        </div>
        {/* end::Body */}
      </section>
      {/* end::Engage widget 4 */}
    </>
  );
}

export default SelfHost;
