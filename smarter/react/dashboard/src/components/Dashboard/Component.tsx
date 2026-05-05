// ----------------------------------------------------------------------------
// Dashboard Component.
// ----------------------------------------------------------------------------
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

interface DashboardProps {
  myResourcesApiUrl: string;
  serviceHealthApiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function Dashboard({ myResourcesApiUrl, serviceHealthApiUrl, csrfCookieName, csrftoken, djangoSessionCookieName, cookieDomain }: DashboardProps) {
  console.log("Dashboard props:", {
    myResourcesApiUrl,
    serviceHealthApiUrl,
    csrfCookieName,
    csrftoken,
    djangoSessionCookieName,
    cookieDomain,
  });
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
            <MyResources apiUrl={myResourcesApiUrl} />
            <div className="col-xl-8 mb-5 mb-xl-10">
              <div className="row g-5 g-xl-10">
                <ServiceHealth apiUrl={serviceHealthApiUrl} />
                <CertificateProgram apiUrl={serviceHealthApiUrl} />
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
            <YTVideo videoId="G2RSCzxxupE" />
          </div>
        </div>
      </section>
    </>
  );
}

export default Dashboard;
