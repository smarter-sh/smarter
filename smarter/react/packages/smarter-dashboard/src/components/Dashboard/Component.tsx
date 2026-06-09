/**
 * Dashboard root layout component.
 *
 * This component composes the main dashboard view by arranging resource,
 * service, certification, tooling, hosting, contribution, and media widgets
 * into responsive Bootstrap grid sections.
 *
 * :param myResourcesApiUrl: API endpoint used by the MyResources widget.
 * :type myResourcesApiUrl: str
 * :param serviceHealthApiUrl: API endpoint used by the ServiceHealth widget.
 * :type serviceHealthApiUrl: str
 * :param csrfCookieName: Cookie name used for CSRF integration.
 * :type csrfCookieName: str
 * :param csrftoken: CSRF token value for authenticated requests.
 * :type csrftoken: str
 * :param djangoSessionCookieName: Django session cookie name.
 * :type djangoSessionCookieName: str
 * :param cookieDomain: Domain scope applied to cookie operations.
 * :type cookieDomain: str
 *
 * :returns: A JSX fragment containing the complete dashboard composition.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Dashboard
 *       myResourcesApiUrl="https://customer.smarter.sh/dashboard/api/my-resources"
 *       serviceHealthApiUrl="https://customer.smarter.sh/dashboard/api/service-health"
 *       csrfCookieName="csrftoken"
 *       csrftoken="token-value"
 *       djangoSessionCookieName="sessionid"
 *       cookieDomain=".smarter.sh"
 *     />
 */
import type { AppContextInterface } from "@/main";

import "./styles.css";
import MyResources from "../MyResources/Component";
import ServiceHealth from "../ServiceHealth/Component";
import CertificateProgram from "../CertificateProgram/Component";
import VSCodeExtension from "../VSCodeExtension/Component";
import Sdk from "../Sdk/Component";
import Cli from "../Cli/Component";
import SelfHost from "../SelfHost/Component";
import Contribute from "../Contribute/Component";
import YTVideo from "../YTVideo/Component";


function Dashboard({ appContext }: { appContext: AppContextInterface }) {

  return (
    <>
      <section
        id="kt_app_content"
        aria-label="Dashboard"
        className="app-content flex-column-fluid"
      >
        <div
          id="kt_app_content_container"
          className="app-container container-xxl"
        >
          <div className="row g-5 g-xl-10 mt-3">
            <MyResources apiUrl={appContext.myResourcesApiUrl} />
            <div className="col-xl-8 mb-5 mb-xl-10">
              <div className="row g-5 g-xl-10">
                <ServiceHealth apiUrl={appContext.serviceHealthApiUrl} />
                <CertificateProgram />
              </div>
              <VSCodeExtension />
            </div>
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <Sdk />
            <Cli />
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <div
              className="col-xl-6 mb-5 mb-xl-10"
              style={{ minHeight: "300px" }}
            >
              <SelfHost />
            </div>
            <div
              className="col-xl-6 mb-5 mb-xl-10"
              style={{ minHeight: "300px" }}
            >
              <Contribute />
            </div>
          </div>

          <div className="row g-5 g-xl-10">
            <YTVideo videoId="YtVxkjHzZrE" />
            <YTVideo videoId="bfePkGzKAvw" />
          </div>
        </div>
      </section>
    </>
  );
}

export default Dashboard;
