/**
 * RecentActivity dashboard widget.
 *
 * This component renders the user's most recent manifest commands that change
 * something (apply, delete, deploy, undeploy), from the Smarter journal, with
 * failed commands highlighted.
 *
 * :param sessionContext: Session context used for authenticated requests.
 * :type sessionContext: SessionContext
 * :param apiUrl: Endpoint used to request the recent activity.
 * :type apiUrl: str
 *
 * :returns: A JSX element containing the recent activity card.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <RecentActivity sessionContext={sessionContext} apiUrl="/dashboard/api/activity/" />
 */
import type { SessionContext } from "@smarter/common";
import { Loading } from "@smarter/common";

import useDashboardApi from "@/hooks/useDashboardApi";
import "./styles.css";

interface ActivityItem {
  created_at: string;
  thing: string;
  command: string;
  status_code: number;
  message: string | null;
}

interface ActivityData {
  journal_enabled: boolean;
  items: ActivityItem[];
}

interface RecentActivityProps {
  sessionContext: SessionContext;
  apiUrl: string;
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const failed = item.status_code >= 400;
  return (
    <tr className={failed ? "recent-activity-failed" : undefined}>
      <td className="text-nowrap text-gray-500 fs-7">{new Date(item.created_at).toLocaleString()}</td>
      <td>
        <span className={`badge ${failed ? "badge-light-danger" : "badge-light-success"} fs-8`}>{item.command}</span>
      </td>
      <td className="fw-bold text-gray-800 fs-7">{item.thing}</td>
      <td className={`fs-7 ${failed ? "text-danger" : "text-gray-600"}`}>{item.message ?? `HTTP ${item.status_code}`}</td>
    </tr>
  );
}

function RecentActivity({ sessionContext, apiUrl }: RecentActivityProps) {
  const { data, error } = useDashboardApi<ActivityData>(sessionContext, apiUrl);

  let body;
  if (error) {
    body = <div className="text-danger fs-7">Failed to load recent activity: {error}</div>;
  } else if (!data) {
    body = <Loading />;
  } else if (data.items.length === 0) {
    body = (
      <div className="text-muted fs-7">
        {data.journal_enabled
          ? "No recent activity. Apply, deploy or delete a manifest and it will show here."
          : "Activity journaling is turned off (waffle switch enable_journal)."}
      </div>
    );
  } else {
    body = (
      <div className="table-responsive">
        <table className="table table-row-dashed align-middle gs-0 gy-2 mb-0">
          <tbody>
            {data.items.map((item, index) => (
              <ActivityRow key={`${item.created_at}-${index}`} item={item} />
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <section id="recent-activity" aria-label="Recent Activity" className="card border-transparent">
      <div className="card-header border-0 pt-5">
        <h3 className="card-title align-items-start flex-column">
          <span className="card-label fw-bold text-gray-900">Recent Activity</span>
          <span className="text-muted mt-1 fw-semibold fs-7">Your latest manifest commands</span>
        </h3>
      </div>
      <div className="card-body pt-3">{body}</div>
    </section>
  );
}

export default RecentActivity;
