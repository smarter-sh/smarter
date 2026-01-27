/*-----------------------------------------------------------------------------
  Handle File Drop for YAML files.

  See sample http response data in:
  - smarter/smarter/apps/api/v1/cli/data/responses/SmarterJournaledJsonResponse.json
  - smarter/smarter/apps/api/v1/cli/data/responses/SmarterJournaledJsonErrorResponse.json.json

    window.workbenchListPath = "{{ drop_zone.workbench_list_path }}";
    window.pluginListPath = "{{ drop_zone.plugin_list_path }}";
    window.connectionListPath = "{{ drop_zone.connection_list_path }}";
    window.providerListPath = "{{ drop_zone.provider_list_path }}";

 -----------------------------------------------------------------------------*/

function showModal(title, message, data, isError = false) {
  if (!document.getElementById("drop-zone-modal")) {
    const outcomeColor = isError ? "#dc3545" : "#28a745";
    const modalHtml = `
      <div id="drop-zone-modal" style="display:none;position:fixed;z-index:9999;left:0;top:0;width:100vw;height:100vh;background:rgba(0,0,0,0.4);justify-content:center;align-items:center;">
        <div style="background:#fff;padding:24px 20px 16px 20px;border-radius:8px;max-width:500px;width:90%;box-shadow:0 2px 16px rgba(0,0,0,0.2);position:relative;">
          <button id="drop-zone-modal-close" style="position:absolute;top:8px;right:12px;font-size:18px;background:none;border:none;cursor:pointer;">&times;</button>
          <div id="drop-zone-modal-title" style="margin-bottom:10px;font-weight:bold;font-size:18px;"></div>
          <div id="drop-zone-modal-message" style="font-size:15px;margin-bottom:10px;color:${outcomeColor};"></div>
          <pre id="drop-zone-modal-data" style="display:none;max-height:200px;overflow:auto;background:#f8f8f8;padding:10px;border-radius:4px;font-size:12px;color:#333;"></pre>
        </div>
      </div>`;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
  }
  const modal = document.getElementById("drop-zone-modal");
  const messageDiv = document.getElementById("drop-zone-modal-message");
  messageDiv.textContent = message || "Unknown outcome :(";
  messageDiv.style.color = isError ? "#dc3545" : "#28a745";

  document.getElementById("drop-zone-modal-title").textContent =
    title || "Smarter Api";
  document.getElementById("drop-zone-modal-close").onclick = function () {
    modal.style.display = "none";
    // navigate to appropriate page based on what was applied
    // Enumerate possible 'thing' values and their redirect paths
    const thingRedirects = [
      { things: ["SqlPlugin", "ApiPlugin", "StaticPlugin"], path: window.pluginListPath },
      { things: ["SqlConnection", "ApiConnection"], path: window.connectionListPath },
      { things: ["Provider"], path: window.providerListPath },
      { things: ["ChatBot"], path: window.workbenchListPath },
    ];
    for (const entry of thingRedirects) {
      if (entry.things.includes(data.thing)) {
        window.location.href = entry.path;
        break;
      }
    }

  };
  if (data) {
    const dataPre = document.getElementById("drop-zone-modal-data");
    dataPre.textContent = JSON.stringify(data, null, 2);
    dataPre.style.display = "block";
  } else {
    document.getElementById("drop-zone-modal-data").style.display = "none";
  }
  modal.style.display = "flex";
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
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
  }, 1000); // match animation duration
  const init = {
    method: "POST",
    headers: {
      "Content-Type": "application/x-yaml",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: yamlContent,
    credentials: "same-origin",
  };
  fetch(apiApplyPath, init)
    .then(async (response) => {
      let data = null;
      let text = null;
      try {
        data = await response.json();
        console.log("Response JSON parsed:", data);
      } catch (e) {
        try {
          text = await response.text();
          console.log("Response text parsed:", text);
        } catch {}
      }
      return { response, data: data || text };
    })
    .then(({ response, data }) => {
      if (!response.ok) {
        overlay.classList.add("drop-zone--error");
        setTimeout(() => {
          overlay.classList.remove("drop-zone--error");
        }, 1200);
        let briefMsg = data.error.description || "Unknown error";
        showModal("Smarter Api Error", briefMsg, data, true);
        throw new Error(briefMsg);
      }
      overlay.classList.add("drop-zone--success");
      setTimeout(() => {
        overlay.classList.remove("drop-zone--success");
      }, 2000);
      return data;
    })
    .then((data) => {
      if (data) {
        showModal(
          "Smarter Api",
          data.message || "Manifest applied successfully.",
          data,
          false,
        );
      }
    })
    .catch((error) => {
      // Only show modal if not already shown
      if (
        !document.getElementById("drop-zone-modal").style.display ||
        document.getElementById("drop-zone-modal").style.display === "none"
      ) {
        showModal("Smarter Api Error", error.message, error.stack || "", true);
      }
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

  window.addEventListener("dragover", function (e) {
    e.preventDefault();
    if (!overlay.classList.contains("drop-zone--hover")) {
      console.log("Drag over detected");
      showOverlay(overlay);
    }
  });

  window.addEventListener("dragleave", function (e) {
    console.log("Drag leave detected");
    e.preventDefault();
    if (e.target === overlay || e.pageX === 0 || e.pageY === 0)
      hideOverlay(overlay);
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
          console.log("YAML file received.");
          applyManifest(overlay, yamlContent);
        };
        reader.readAsText(file);
      } else {
        alert("Please drop a Smarter YAML manifest file (.yaml or .yml)");
      }
    }
  });
});
