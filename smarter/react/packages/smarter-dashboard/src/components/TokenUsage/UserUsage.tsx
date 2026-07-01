import {TokenUsageChart} from "./Chart";
import {data, areas, lines} from "./data";
import "./styles.css";

interface UserUsageProps {
}

function UserUsage({  }: UserUsageProps) {
  return (
    <>
      <div id="user-usage" aria-label="User Usage" className="col-xl-12 mb-5 mb-xl-10">
        {/* begin::User Usage */}
        <div className="card border-transparent" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100">
            {/* begin::Title */}
            <h6 className="text-muted  opacity-75-hover w-100 my-4 fs-3 fw-bold">
              User Token Usage
            </h6>
            <TokenUsageChart data={data} areas={areas} lines={lines} />
          </div>
        </div>
      </div>
    </>
  );
}

export default UserUsage;
