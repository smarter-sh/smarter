import type { TabKey } from "@/lib/Types";

interface TabNavProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  tabs: { key: TabKey; label: string }[];
}

export const TabNav: React.FC<TabNavProps> = ({ activeTab, onTabChange, tabs }) => (
  <ul className="nav nav-tabs">
    {Array.isArray(tabs) &&
      tabs.map((tab) => (
        <li className="nav-item" key={tab.key}>
          <button
            className={`nav-link${activeTab === tab.key ? " active" : ""}`}
            onClick={() => onTabChange(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        </li>
      ))}
  </ul>
);
