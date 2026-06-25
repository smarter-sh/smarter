/**
 * DropZone root layout component.
 *
 * This component composes the main drop-zone view by arranging resource,
 * service, certification, tooling, hosting, contribution, and media widgets
 * into responsive Bootstrap grid sections.
 *
 * :returns: A JSX fragment containing the complete drop-zone composition.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <DropZone sessionContext={sessionContext} />
 */
import { useEffect, useRef, useState } from "react";
import { load } from "js-yaml";

import { fetchDjangoUrl } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix } from "@/const";

import "./styles.css";

type DropZoneProps = {
  sessionContext: SessionContext;
};

export default function DropZone({ sessionContext }: DropZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  useEffect(() => {
    const handleWindowDragOver = (event: DragEvent) => {
      event.preventDefault();

      if (!isDragActive) {
        setIsDragActive(true);
      }
    };

    const handleWindowDragLeave = (event: DragEvent) => {
      event.preventDefault();

      if (event.clientX === 0 && event.clientY === 0) {
        setIsDragActive(false);
      }
    };

    const handleWindowDrop = (event: DragEvent) => {
      event.preventDefault();
      setIsDragActive(false);
    };

    window.addEventListener("dragover", handleWindowDragOver);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);

    return () => {
      window.removeEventListener("dragover", handleWindowDragOver);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
    };
  }, [isDragActive]);

  async function validateAndReadManifest(file: File): Promise<string> {
    if (!/\.(yaml|yml)$/i.test(file.name)) {
      throw new Error("Please select a Smarter YAML manifest file (.yaml or .yml)");
    }

    const content = await file.text();

    try {
      const obj = load(content);
      const json = JSON.stringify(obj);
      return json;
    } catch (error) {
      throw new Error(`Invalid YAML syntax: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async function applyManifest(manifest: string) {
    const response = await fetchDjangoUrl(sessionContext, sessionContext.ApiUrl, manifest);
    const data = await response.json();
    console.debug(loggerPrefix, `fetched response from ${sessionContext.ApiUrl}:`, data);

    if (!response.ok) {
      throw new Error(`Manifest apply failed (${response.status})`);
    }

    return data;
  }

  async function processFile(file: File) {
    setIsUploading(true);

    try {
      const manifest = await validateAndReadManifest(file);
      await applyManifest(manifest);
    } finally {
      setIsUploading(false);
    }
  }

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    try {
      if (file) {
        await processFile(file);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to process manifest");
    } finally {
      event.target.value = "";
    }
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();

    setIsDragActive(false);

    const file = event.dataTransfer.files?.[0];

    try {
      if (file) {
        await processFile(file);
      }
    } catch (error) {
      alert(error instanceof Error ? error.message : "Failed to process manifest");
    }
  };

  const handleOverlayDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  return (
    <section id="manifest-apply">
      <div id="kt_app_content" className="app-content flex-column-fluid">
        <div id="kt_app_content_container" className="app-container container-xxl">
          <div className="row g-5 g-xl-10">
            <div className="col-xl-8 mb-5 mb-xl-10">
              <div className="g-5 g-xl-10 mb-l-10">
                <h3 className="pt-5">Apply Smarter YAML Manifest</h3>

                <div className="file-open-command-button mt-5 mb-5">
                  <div className="col-10" />

                  <div className="col-2">
                    <input ref={fileInputRef} type="file" accept=".yaml,.yml" hidden onChange={handleFileSelected} />

                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      disabled={isUploading}
                      onClick={openFileDialog}
                    >
                      {isUploading ? "Uploading..." : "File Open"}
                    </button>
                  </div>
                </div>
                <div
                  id="drop-zone-overlay"
                  className={`manifest-drop-zone d-flex justify-content-center align-items-center ${isDragActive ? "drop-zone--hover" : ""}`}
                  onDragOver={handleOverlayDragOver}
                  onDrop={handleDrop}
                >
                  <span>{isUploading ? "Uploading..." : "Drop Zone"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
