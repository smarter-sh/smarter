"use strict";

// clear form
document.querySelector("#input-email").addEventListener("focus", function () {
  console.log("Input field focused");
  document.getElementById("error-message").textContent = "";
});
document
  .querySelector("#input-password")
  .addEventListener("focus", function () {
    console.log("Input field focused");
    document.getElementById("error-message").textContent = "";
  });

// Class definition
var KTSigninGeneral = (function () {
  // Elements
  var form;
  var submitButton;
  var validator;

  // Handle form
  var handleValidation = function (e) {
    // Init form validation rules. For more info check the FormValidation plugin's official documentation:https://formvalidation.io/
    validator = FormValidation.formValidation(form, {
      fields: {
        email: {
          validators: {
            regexp: {
              regexp: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: "The value is not a valid email address",
            },
            notEmpty: {
              message: "Email address is required",
            },
          },
        },
        password: {
          validators: {
            notEmpty: {
              message: "The password is required",
            },
          },
        },
      },
      plugins: {
        trigger: new FormValidation.plugins.Trigger(),
        bootstrap: new FormValidation.plugins.Bootstrap5({
          rowSelector: ".fv-row",
          eleInvalidClass: "", // comment to enable invalid state icons
          eleValidClass: "", // comment to enable valid state icons
        }),
      },
    });
  };

  var handleSubmit = function (e) {
    // Handle form submit
    submitButton.addEventListener("click", function (e) {
      // Prevent button default action
      e.preventDefault();

      // Validate form
      validator.validate().then(function (status) {
        if (status == "Valid") {
          // Show loading indication
          submitButton.setAttribute("data-kt-indicator", "on");

          // Disable button to avoid multiple click
          submitButton.disabled = true;

          // Simulate ajax request
          setTimeout(function () {
            // Hide loading indication
            submitButton.removeAttribute("data-kt-indicator");

            // Enable button
            submitButton.disabled = false;

            // Smarter event handler.
            var formData = new FormData(form);
            const csrftoken = getSmarterCsrfToken();
            fetch("/login/", {
              method: "POST",
              headers: {
                "X-CSRFToken": csrftoken,
              },
              body: formData,
            })
              .then((response) => {
                if (response.ok) {
                  window.location.href = "/";
                }
                if (response.status === 401) {
                  var div = document.querySelector("#error-message");
                  div.innerHTML = "incorrect username or password.";
                } else if (response.status === 403) {
                  var div = document.querySelector("#error-message");
                  div.innerHTML = "user not found.";
                } else {
                  throw new Error(`HTTP error status: ${response.status}`);
                }
              })
              .catch((error) => {
                console.error("Error:", error);
              });
          }, 500);
        } else {
          // Show error popup. For more info check the plugin's official documentation: https://sweetalert2.github.io/
          Swal.fire({
            text: "Sorry, looks like there are some errors detected, please try again.",
            icon: "error",
            buttonsStyling: false,
            confirmButtonText: "Ok, got it!",
            customClass: {
              confirmButton: "btn btn-primary",
            },
          });
        }
      });
    });
  };

  var isValidUrl = function (url) {
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  };

  // Public functions
  return {
    // Initialization
    init: function () {
      form = document.querySelector("#kt_sign_in_form");
      submitButton = document.querySelector("#kt_sign_in_submit");

      handleValidation();

      if (isValidUrl(submitButton.closest("form").getAttribute("action"))) {
        handleSubmitAjax(); // use for ajax submit
      } else {
        handleSubmit(); // used for demo purposes only
      }
    },
  };
})();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  KTSigninGeneral.init();
});
