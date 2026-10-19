/**
 * The Console's "Architecture" tab: the tree of the SAM resources that the LLMClient is built from, as cards that
 * open each resource's manifest in a new tab. It fetches the tree when it is first opened, and again when its
 * Reload button is pressed, e.g. after a manifest was changed in another tab.
 */
import { useState } from "react";
import { Loading } from "@smarter/common";
import { LLMClientArchitecture } from "@smarter/llmclient-architecture";

import TabError from "@/components/Console/TabError";
import { useTabData } from "@/components/Console/useTabData";
import { fetchArchitecture } from "@/lib/api";
import type { WorkbenchConfig } from "@/lib/types";

function ArchitectureTree({ url, onReload }: { url: string; onReload: () => void }) {
  const { data: tree, error } = useTabData(() => fetchArchitecture(url));
  if (error) return <TabError error={error} />;
  if (tree === null) return <Loading />;
  return <LLMClientArchitecture tree={tree} onReload={onReload} />;
}

function ArchitectureTab({ workbench }: { workbench: WorkbenchConfig }) {
  // a new key mounts the tree again, which fetches it again.
  const [generation, setGeneration] = useState(0);
  return (
    <div className="console-architecture-page">
      <ArchitectureTree
        key={generation}
        url={workbench.architectureUrl ?? ""}
        onReload={() => setGeneration((current) => current + 1)}
      />
    </div>
  );
}

export default ArchitectureTab;
