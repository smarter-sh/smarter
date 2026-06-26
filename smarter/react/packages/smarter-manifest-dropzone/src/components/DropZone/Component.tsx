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
import DropZoneModal from "@/components/Modal";

import "./styles.css";

type DropZoneProps = {
  sessionContext: SessionContext;
};

type Manifest = Record<string, any>;

type ModalState = {
  open: boolean;
  title: string;
  data?: any;
  isError?: boolean;
};


export default function DropZone({ sessionContext }: DropZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const [modal, setModal] = useState<ModalState>({
    open: false,
    title: "",
    data: null,
    isError: false,
  });

  const openFileDialog = () => fileInputRef.current?.click();

  const showModal = (title: string, data: any, isError = false) => {
    setModal({
      open: true,
      title,
      data,
      isError,
    });
  };

  useEffect(() => {
    const onDragOver = (e: DragEvent) => {
      e.preventDefault();
      setIsDragActive(true);
    };

    const onDragLeave = (e: DragEvent) => {
      e.preventDefault();
      if (e.clientX === 0 && e.clientY === 0) {
        setIsDragActive(false);
      }
    };

    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsDragActive(false);
    };

    window.addEventListener("dragover", onDragOver);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("drop", onDrop);

    return () => {
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, []);

  function validateManifest(manifest: Manifest) {
    if (!manifest || typeof manifest !== "object") {
      throw new Error("Manifest is not a valid object");
    }

    if (!manifest.metadata?.name) {
      throw new Error("Missing metadata.name");
    }

    if (!manifest.apiVersion) {
      throw new Error("Missing apiVersion");
    }

    if (!manifest.apiVersion.startsWith("smarter.sh/v")) {
      throw new Error("Invalid apiVersion");
    }

    if (!manifest.kind) {
      throw new Error("Missing kind");
    }
  }

  async function parseManifest(file: File): Promise<Manifest> {
    const content = await file.text();
    const obj = load(content);
    return JSON.parse(JSON.stringify(obj)) as Manifest;
  }

  async function applyManifest(manifest: Manifest) {
    const response = await fetchDjangoUrl(sessionContext, sessionContext.ApiUrl, JSON.stringify(manifest));

    const data = await response.json();

    if (!response.ok) {
      throw new Error(`Manifest apply failed (${response.status})`);
    }

    return data;
  }

  async function processFile(file: File) {
    setIsUploading(true);

    try {
      const manifest = await parseManifest(file);

      validateManifest(manifest);
      const result = await applyManifest(manifest);

      showModal("Manifest Applied", result, false);
    } catch (error) {
      console.error(loggerPrefix, error);

      showModal("Manifest Apply Failed", error instanceof Error ? error.message : "Unknown error", true);
    } finally {
      setIsUploading(false);
    }
  }

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    try {
      if (file) await processFile(file);
    } finally {
      event.target.value = "";
    }
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragActive(false);

    const file = event.dataTransfer.files?.[0];

    try {
      if (file) await processFile(file);
    } catch (error) {
      showModal("Error", error instanceof Error ? error.message : "Failed", true);
    }
  };

  return (
    <section id="manifest-apply">
      <div className="app-content flex-column-fluid">
        <div className="app-container container-xxl">
          <h3 className="pt-5">Apply Smarter YAML Manifest</h3>

          <input ref={fileInputRef} type="file" accept=".yaml,.yml" hidden onChange={handleFileSelected} />

          <button type="button" className="btn btn-sm btn-primary" disabled={isUploading} onClick={openFileDialog}>
            {isUploading ? "Uploading..." : "File Open"}
          </button>

          <div
            className={`manifest-drop-zone d-flex justify-content-center align-items-center ${
              isDragActive ? "drop-zone--hover" : ""
            }`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <span>{isUploading ? "Uploading..." : "Drop Zone"}</span>
          </div>

          <DropZoneModal
            {...modal}
            onClose={() => setModal((m) => ({ ...m, open: false }))}
          />
        </div>
      </div>
    </section>
  );
}
