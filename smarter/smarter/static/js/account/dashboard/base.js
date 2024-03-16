"use strict";

// Class definition
var KTProfileGeneral = (function () {
  // Private declarations
  var shortcutSelect;
  var shortcutOptionUser;
  var shortcutOptionApiKey;
  var shortcutOptionPaymentMethod;
  var shortcutLink;

  var initTabHandler = function () {
    // Add event listener to each navigation link
    document.querySelectorAll(".nav-item a").forEach(function (link) {
      link.addEventListener("click", function () {
        // Store the clicked link's pathname in local storage
        localStorage.setItem("activeLink", this.pathname);
      });
    });

    // Add 'active' class to the link that matches the pathname stored in local storage
    window.addEventListener("DOMContentLoaded", (event) => {
      var activeLink = localStorage.getItem("activeLink");

      document.querySelectorAll(".nav-item a").forEach(function (link) {
        if (link.pathname === activeLink) {
          link.classList.add("active");
        } else {
          link.classList.remove("active");
        }
      });
    });
  };

  var initShortcutSelectHandler = function () {

    $("#shortcut_select").on("select2:select", function (e) {
      var selectedOption = e.params.data.id;
      var newHref = shortcutLink.href;

      if (selectedOption === "user") {
        newHref = "/account/dashboard/users/new/";
      }

      if (selectedOption === "api_key") {
        newHref = "/account/dashboard/api-keys/new/";
      }

      if (selectedOption === "payment_method") {
        newHref = "/account/dashboard/payment-methods/new/";
      }
      shortcutLink.href = newHref;
    });
  };

  // Public methods
  return {
    init: function () {
      // Init shortcuts
      shortcutSelect = document.querySelector("#shortcut_select");
      shortcutOptionUser = document.querySelector("#shortcut_option_user");
      shortcutOptionApiKey = document.querySelector("#shortcut_option_api_key");
      shortcutOptionPaymentMethod = document.querySelector(
        "#shortcut_option_payment_method",
      );
      shortcutLink = document.querySelector("#shortcut_link");

      initTabHandler();
      initShortcutSelectHandler();
    },
  };
})();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  KTProfileGeneral.init();
});
