/**
 * Dashboard root layout component.
 *
 * This component composes the main dashboard view by arranging budget alerts, the
 * global search, resource, service health, quick action, extensions, onboarding, activity,
 * usage and budget widgets into responsive Bootstrap grid sections, followed
 * by the static informational widgets: new features, instructor resources,
 * SDKs, integrations, the CLI, the VS Code extension, the MCP server, hosting
 * and contribution.
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
 *       myResourcesApiUrl="https://customer.smarter.sh/api/web/dashboard/my-resources"
 *       serviceHealthApiUrl="https://customer.smarter.sh/api/web/dashboard/service-health"
 *       csrfCookieName="csrftoken"
 *       csrftoken="token-value"
 *       djangoSessionCookieName="sessionid"
 *       cookieDomain=".smarter.sh"
 *     />
 */
import type { AppContextInterface } from "../../Types";

import "./styles.css";
import MyResources from "../MyResources/Component";
import ServiceHealth from "../ServiceHealth/Component";
import QuickActions from "../QuickActions/Component";
import GlobalSearch from "../GlobalSearch/Component";
import GettingStarted from "../GettingStarted/Component";
import RecentActivity from "../RecentActivity/Component";
import BudgetAlerts from "../BudgetAlerts/Component";
import UserCharges from "../TokenUsage";
import BudgetVsActual from "../BudgetVsActual";
import { gettext } from "@smarter/common";
import {
  Cli,
  Contribute,
  Extensions,
  Instructors,
  Integrations,
  McpServer,
  Sdk,
  SelfHost,
  VSCodeExtension,
  WhatsNew,
} from "@smarter.sh/ui-widgets";

function Dashboard({ appContext }: { appContext: AppContextInterface }) {
  return (
    <>
      {/* the console's layout gives the page the theme's app-content and app-container. */}
      <section aria-label={gettext("Dashboard")}>
        <div>
          {appContext.budgetsApiUrl && (
            <BudgetAlerts sessionContext={appContext.sessionContext} apiUrl={appContext.budgetsApiUrl} />
          )}

          {appContext.globalSearchApiUrl && (
            <div className="row g-5 g-xl-10 mt-3">
              <GlobalSearch sessionContext={appContext.sessionContext} apiUrl={appContext.globalSearchApiUrl} />
            </div>
          )}

          <div className="row g-5 g-xl-10 mt-3">
            <MyResources apiUrl={appContext.myResourcesApiUrl} />
            <div className="col-xl-8 mb-5 mb-xl-10">
              <div className="row g-5 g-xl-10">
                <ServiceHealth sessionContext={appContext.sessionContext} apiUrl={appContext.serviceHealthApiUrl} />
                <QuickActions sessionContext={appContext.sessionContext} apiUrl={appContext.quickActionsApiUrl} />
              </div>
              <Extensions />
            </div>
          </div>

          <GettingStarted sessionContext={appContext.sessionContext} apiUrl={appContext.gettingStartedApiUrl} />

          <div className="row g-5 g-xl-10">
            <div className="col-xl-12 mb-5 mb-xl-10">
              <RecentActivity sessionContext={appContext.sessionContext} apiUrl={appContext.activityApiUrl} />
            </div>
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <UserCharges
              sessionContext={appContext.sessionContext}
              apiUrl={appContext.chargesApiUrl}
              className={appContext.budgetsApiUrl ? "col-xl-6" : "col-xl-12"}
            />
            {appContext.budgetsApiUrl && (
              <BudgetVsActual
                sessionContext={appContext.sessionContext}
                apiUrl={appContext.budgetsApiUrl}
                className="col-xl-6"
              />
            )}
          </div>

          {/* static widgets */}
          <div className="row g-5 g-xl-10">
            <div className="col-xl-6 mb-5 mb-xl-10">
              <WhatsNew />
            </div>
            <Instructors />
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <Sdk />
            <Integrations />
            <Cli />
          </div>

          <div className="row g-5 g-xl-10 align-items-stretch">
            <div className="col-xl-8 mb-5 mb-xl-10">
              <VSCodeExtension />
            </div>
            <div className="col-xl-4 mb-5 mb-xl-10">
              <McpServer />
            </div>
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
