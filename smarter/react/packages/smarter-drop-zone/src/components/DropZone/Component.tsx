/**
 * DropZone root layout component.
 *
 * This component composes the main drop-zone view by arranging resource,
 * service, certification, tooling, hosting, contribution, and media widgets
 * into responsive Bootstrap grid sections.
 *
 * :returns: A JSX fragment containing the complete drop-zone composition.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <DropZone
 *       apiUrl="https://customer.smarter.sh/drop-zone/api/my-resources"
 *       csrfCookieName="csrftoken"
 *       csrftoken="token-value"
 *       djangoSessionCookieName="sessionid"
 *       cookieDomain=".smarter.sh"
 *     />
 */
import type { SessionContext } from "@smarter/common";

import "./styles.css";


function DropZone({ sessionContext }: { sessionContext: SessionContext }) {

  return (
    <>
      <section
        id="kt_app_content"
        aria-label="DropZone"
        className="app-content flex-column-fluid"
      >
        <div
          id="kt_app_content_container"
          className="app-container container-xxl"
        >
          <div className="row g-5 g-xl-10 mt-3">hello world sessionContext: {JSON.stringify(sessionContext)}</div>
        </div>
      </section>
    </>
  );
}

export default DropZone;
