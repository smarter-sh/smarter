"use strict";

// The copy buttons of the page that a browser sees at a deployed LLMClient's endpoints:
// templates/llmclient/endpoints.html. ClipboardJS is in the global plugins bundle.
//
// Each button names what it copies, in data-clipboard-target, and the word that it shows for a
// moment afterwards, in data-smarter-copied-label. The label comes from the template, already
// translated: these hosts load no JavaScript catalog, so gettext() is not defined here.
var SmarterLLMClientEndpoints = (function () {
  var COPIED_SECONDS = 1.5;

  var init = function () {
    var clipboard = new ClipboardJS("[data-clipboard-target]");

    clipboard.on("success", function (e) {
      var button = e.trigger;
      var label = button.getAttribute("data-smarter-copy-label") || button.textContent;
      button.setAttribute("data-smarter-copy-label", label);
      button.textContent = button.getAttribute("data-smarter-copied-label") || label;
      e.clearSelection();
      setTimeout(function () {
        button.textContent = label;
      }, COPIED_SECONDS * 1000);
    });
  };

  return { init: init };
})();

KTUtil.onDOMContentLoaded(function () {
  SmarterLLMClientEndpoints.init();
});
