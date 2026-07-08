type WorkbenchHelpProps = {
  title: string;
  icon: string;
  docsUrl: string;
  helpText: string;
};

export default function WorkbenchHelp({ title, icon, docsUrl, helpText }: WorkbenchHelpProps) {
  return (
    <div className="pt-5 pb-5">
      {/* Modeled on a Sphinx/Read the Docs "note" admonition: tinted fill,
          colored left rule, thin border everywhere else. Reads as a callout
          referencing docs, not a promo card -- no shadow, no full-bleed width. */}
      <div
        className="d-flex align-items-start bg-light-primary border border-primary border-opacity-25 border-start border-start-4 border-start-primary rounded-1 px-6 py-5 w-100"
        style={{ maxWidth: 900 }}
      >
        <i className={`ki-outline ${icon} fs-2x text-primary me-4 mt-1 flex-shrink-0`} />

        <div className="flex-grow-1 min-w-0">
          <div className="d-flex align-items-center justify-content-between flex-wrap-reverse gap-2 mb-2">
            <h3 className="fs-6 fw-bold text-gray-800 mb-0">{title}</h3>

            {/* Deep link into a large (~1,500 page) Read the Docs site. Lives
                inside the box now so it reads as part of the callout, not a
                page-level action floating in the header. */}
            <a
              href={docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="fs-7 fw-semibold text-primary text-hover-primary text-nowrap"
            >
              View documentation&nbsp;&#8599;
            </a>
          </div>

          <p className="fs-6 text-gray-700 mb-0 lh-lg">{helpText}</p>
        </div>
      </div>
    </div>
  );
}
