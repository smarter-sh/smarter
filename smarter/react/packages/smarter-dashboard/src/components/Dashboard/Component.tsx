/**
 * Dashboard root layout component.
 *
 * This component composes the main dashboard view by arranging budget alerts,
 * resource, service health, quick action, onboarding, activity and usage
 * widgets into responsive Bootstrap grid sections, followed by the static
 * informational widgets: new features, certification, tooling, hosting and
 * contribution.
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
import QuickActions from "../QuickActions/Component";
import CertificateProgram from "../CertificateProgram/Component";
import VSCodeExtension from "../VSCodeExtension/Component";
import WhatsNew from "../WhatsNew/Component";
import GettingStarted from "../GettingStarted/Component";
import RecentActivity from "../RecentActivity/Component";
import BudgetAlerts from "../BudgetAlerts/Component";
import Sdk from "../Sdk/Component";
import Cli from "../Cli/Component";
import SelfHost from "../SelfHost/Component";
import Contribute from "../Contribute/Component";
import UserCharges from "../TokenUsage/";
import BudgetVsActual from "../BudgetVsActual/";

function Dashboard({ appContext }: { appContext: AppContextInterface }) {
  return (
    <>
      <section id="kt_app_content" aria-label="Dashboard" className="app-content flex-column-fluid">
        <div id="kt_app_content_container" className="app-container container-xxl">
          {appContext.budgetsApiUrl && (
            <BudgetAlerts sessionContext={appContext.sessionContext} apiUrl={appContext.budgetsApiUrl} />
          )}

          <div className="row g-5 g-xl-10 mt-3">
            <MyResources apiUrl={appContext.myResourcesApiUrl} />
            <div className="col-xl-8 mb-5 mb-xl-10">
              <div className="row g-5 g-xl-10">
                <ServiceHealth apiUrl={appContext.serviceHealthApiUrl} />
                <QuickActions sessionContext={appContext.sessionContext} apiUrl={appContext.quickActionsApiUrl} />
              </div>
              <VSCodeExtension />
            </div>
          </div>

          <GettingStarted sessionContext={appContext.sessionContext} apiUrl={appContext.gettingStartedApiUrl} />

          <div className="row g-5 g-xl-10">
            <div className="col-xl-12 mb-5 mb-xl-10">
              <RecentActivity sessionContext={appContext.sessionContext} apiUrl={appContext.activityApiUrl} />
            </div>
          </div>

          <div className="row g-5 g-xl-10">
            <div className="col-xl-12 mb-5 mb-xl-10">
              <UserCharges sessionContext={appContext.sessionContext} apiUrl={appContext.chargesApiUrl} />
            </div>
          </div>

          {appContext.budgetsApiUrl && (
            <div className="row g-5 g-xl-10">
              <BudgetVsActual sessionContext={appContext.sessionContext} apiUrl={appContext.budgetsApiUrl} />
            </div>
          )}

          {/* static widgets */}
          <div className="row g-5 g-xl-10">
            <div className="col-xl-6 mb-5 mb-xl-10">
              <WhatsNew />
            </div>
            <CertificateProgram />
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <Sdk />
            <Cli />
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <div className="col-xl-6 mb-5 mb-xl-10" style={{ minHeight: "300px" }}>
              <SelfHost />
            </div>
            <div className="col-xl-6 mb-5 mb-xl-10" style={{ minHeight: "300px" }}>
              <Contribute />
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export default Dashboard;
