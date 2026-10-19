/**
 * The Console's "Manifest" tab: the LLMClient's manifest, in the web console's manifest editor, which saves,
 * clones and deletes it with the cli api. It fetches the manifest when it is first opened. When the editor saves
 * the manifest, the chat reloads the LLMClient's configuration. When it deletes the LLMClient, the workbench, whose
 * LLMClient is gone, leaves for the LLM Clients list.
 */
import { Loading } from "@smarter/common";
import { ManifestEditor } from "@smarter/manifest-editor";

import TabError from "@/components/Console/TabError";
import { useTabData } from "@/components/Console/useTabData";
import { fetchManifest } from "@/lib/api";
import type { WorkbenchConfig } from "@/lib/types";

interface ManifestTabProps {
  workbench: WorkbenchConfig;
  /** Called when the editor saves the manifest. */
  onSaved?: () => void;
}

function ManifestTab({ workbench, onSaved }: ManifestTabProps) {
  const { data: manifest, error } = useTabData(() => fetchManifest(workbench.manifestUrl ?? ""));
  if (error) return <TabError error={error} />;
  if (manifest === null) return <Loading />;
  return (
    <div className="console-manifest-editor">
      <ManifestEditor
        sessionContext={workbench.session}
        initialManifest={manifest}
        applyApiUrl={workbench.applyApiUrl}
        validateApiUrl={workbench.validateApiUrl}
        deleteApiUrl={workbench.deleteApiUrl}
        kindPlaceholder={workbench.kindPlaceholder}
        onSaved={() => onSaved?.()}
        onDeleted={() => window.location.assign(workbench.llmclientListUrl)}
      />
    </div>
  );
}

export default ManifestTab;
