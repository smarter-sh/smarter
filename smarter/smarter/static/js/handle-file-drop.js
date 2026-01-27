//-----------------------------------------------------------------------------
// Handle File Drop for YAML files
//-----------------------------------------------------------------------------

// Modal dialog logic
function showErrorModal(httpCode, briefMsg, stackTrace) {
  const modal = document.getElementById("error-modal");
  document.getElementById("error-modal-code").textContent =
    `HTTP Status: ${httpCode}`;
  document.getElementById("error-modal-message").textContent = briefMsg;
  document.getElementById("error-modal-trace").textContent = stackTrace || "";
  document.getElementById("error-modal-trace").style.display = "none";
  const toggleBtn = document.getElementById("error-modal-toggle-trace");
  toggleBtn.textContent = "Show Stack Trace";
  toggleBtn.onclick = function () {
    const trace = document.getElementById("error-modal-trace");
    if (trace.style.display === "none") {
      trace.style.display = "block";
      toggleBtn.textContent = "Hide Stack Trace";
    } else {
      trace.style.display = "none";
      toggleBtn.textContent = "Show Stack Trace";
    }
  };
  document.getElementById("error-modal-close").onclick = function () {
    modal.style.display = "none";
  };
  modal.style.display = "flex";
}

function injectHtmlModal() {
  if (!document.getElementById("error-modal")) {
    const modalHtml = `
      <div id="error-modal" style="display:none;position:fixed;z-index:9999;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.5);justify-content:center;align-items:center;">
        <div style="background:#fff;padding:24px 20px 16px 20px;border-radius:8px;max-width:500px;width:90%;box-shadow:0 2px 16px rgba(0,0,0,0.2);position:relative;">
          <button id="error-modal-close" style="position:absolute;top:8px;right:12px;font-size:18px;background:none;border:none;cursor:pointer;">&times;</button>
          <div style="margin-bottom:10px;font-weight:bold;font-size:18px;">Error</div>
          <div id="error-modal-code" style="font-size:14px;color:#b00;margin-bottom:6px;"></div>
          <div id="error-modal-message" style="font-size:15px;margin-bottom:10px;"></div>
          <button id="error-modal-toggle-trace" style="background:#eee;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:13px;margin-bottom:8px;">Show Stack Trace</button>
          <pre id="error-modal-trace" style="display:none;max-height:200px;overflow:auto;background:#f8f8f8;padding:10px;border-radius:4px;font-size:12px;color:#333;"></pre>
        </div>
      </div>`;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
  }
}


function showOverlay(overlay) {
  console.log("Showing overlay");
  overlay.style.display = "block";
  overlay.style.pointerEvents = "auto";
  overlay.classList.add("drop-zone--hover");
}
function hideOverlay(overlay) {
  console.log("Hiding overlay");
  overlay.style.display = "none";
  overlay.style.pointerEvents = "none";
  overlay.classList.remove("drop-zone--hover");
}

function applyManifest(overlay, yamlContent) {
  // Post the YAML content to the server:
  // /api/v1/cli/apply/
  console.log("Applying manifest via API:", apiApplyPath);
  overlay.classList.add("drop-zone--dropped");
  setTimeout(() => {
    overlay.classList.remove("drop-zone--dropped");
  }, 600); // match animation duration
  fetch(apiApplyPath, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-yaml",
    },
    body: yamlContent,
    credentials: "same-origin",
  })
    .then(async (response) => {
      if (!response.ok) {
        overlay.classList.add("drop-zone--error");
        setTimeout(() => {
          overlay.classList.remove("drop-zone--error");
        }, 1200);
        let stackTrace = "";
        let briefMsg = response.statusText || "Unknown error";
        try {
          const data = await response.json();
          if (data && data.error) {
            briefMsg = data.error;
          }
          if (data && data.traceback) {
            stackTrace = data.traceback;
          }
        } catch (e) {
          // Try to get text if not JSON
          try {
            const text = await response.text();
            stackTrace = text;
          } catch {}
        }
        showErrorModal(response.status, briefMsg, stackTrace);
        throw new Error(briefMsg);
      }
      overlay.classList.add("drop-zone--success");
      setTimeout(() => {
        overlay.classList.remove("drop-zone--success");
      }, 1200);
      return response.json();
    })
    .then((data) => {
      console.log("Success:", data);
      alert("YAML file applied successfully!");
    })
    .catch((error) => {
      // Only show modal if not already shown
      if (
        !document.getElementById("error-modal").style.display ||
        document.getElementById("error-modal").style.display === "none"
      ) {
        showErrorModal("N/A", error.message, error.stack || "");
      }
      console.error("Error:", error);
    });

}

document.addEventListener("DOMContentLoaded", function () {
  // File drop event handlers.
  // Get configuration from global variables set in the template
  // (base.html) and/or the DOM
  const dropzoneEnabled = window.dropzoneEnabled;
  const apiApplyPath = window.apiApplyPath;
  const overlay = document.getElementById("drop-zone-overlay");

  if (!dropzoneEnabled) {
    console.log("File drop zone disabled");
    return;
  }
  console.log("File drop zone enabled:", window.dropzoneEnabled);

  injectHtmlModal();

  window.addEventListener("dragover", function (e) {
    console.log("Drag over detected");
    e.preventDefault();
    showOverlay(overlay);
  });

  window.addEventListener("dragleave", function (e) {
    console.log("Drag leave detected");
    e.preventDefault();
    if (e.target === overlay || e.pageX === 0 || e.pageY === 0) hideOverlay(overlay);
  });

  window.addEventListener("drop", function (e) {
    console.log("File drop detected");
    e.preventDefault();
    hideOverlay(overlay);
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith(".yaml") || file.name.endsWith(".yml")) {
        const reader = new FileReader();
        reader.onload = function (evt) {
          const yamlContent = evt.target.result;
          console.log("YAML file content:", yamlContent);
          applyManifest(overlay, yamlContent);
        };
        reader.readAsText(file);
      } else {
        alert("Please drop a Smarter YAML manifest file (.yaml or .yml)");
      }
    }
  });
});
