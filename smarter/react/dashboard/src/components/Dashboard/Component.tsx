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
  apiUrl: string;
}

function Dashboard({ apiUrl }: DashboardProps) {
  return (
    <>
      <section className="dashboard" aria-label="Dashboard">
        <div id="kt_app_content" className="app-content flex-column-fluid">
          {/* begin::Content container */}
          <div
            id="kt_app_content_container"
            className="app-container container-xxl"
          >
            {/* begin::Row */}
            <section className="row g-5 g-xl-10 mt-3">
              <MyResources apiUrl={apiUrl} />
              {/* begin::Col */}
              <div className="col-xl-8 mb-5 mb-xl-10">
                {/* begin::Row */}
                <div className="row g-5 g-xl-10">
                  <ServiceHealth apiUrl={apiUrl} />
                  <CertificateProgram apiUrl={apiUrl} />
                </div>
                {/* end::Row */}
                <VSCodeExtension apiUrl={apiUrl} />
              </div>
              {/* end::Col */}
            </section>
            {/* end::Row */}

            {/* begin::Row downloads */}
            <section className="row g-5 g-xl-10 align-items-stretch">
              <Sdk apiUrl={apiUrl} />
              <Cli apiUrl={apiUrl} />
            </section>
            {/* end::Row downloads */}

            {/* begin::Row install/contribute */}
            <section className="row g-5 g-xl-10 align-items-stretch">
              <div
                className="col-xl-6 mb-5 mb-xl-10"
                style={{ minHeight: "300px" }}
              >
                <SelfHost apiUrl={apiUrl} />
              </div>
              <div
                className="col-xl-6 mb-5 mb-xl-10"
                style={{ minHeight: "300px" }}
              >
                <Contribute apiUrl={apiUrl} />
              </div>
            </section>
            {/* end::Row install/contribute */}

            {/* begin::Row yt videos */}
            <div className="row g-5 g-xl-10">
              <YTVideo apiUrl={apiUrl} />
              <YTVideo apiUrl={apiUrl} />
            </div>
            {/* end::Row yt videos */}
          </div>
          {/* end::Content container */}
        </div>
      </section>
      {/* end::Content container */}
    </>
  );
}

export default Dashboard;
