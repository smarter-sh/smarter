"use strict";

// Class Definition
var KTAuthResetPassword = (function () {
  // Elements
  var form;
  var submitButton;
  var validator;

  var handleForm = function (e) {
    // Init form validation rules. For more info check the FormValidation plugin's official documentation:https://formvalidation.io/
    validator = FormValidation.formValidation(form, {
      fields: {
        email: {
          validators: {
            regexp: {
              regexp: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
              message: "Not a valid email address",
            },
            notEmpty: {
              message: "Please type your email address",
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

  var handleSubmitAjax = function (e) {
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
          const csrftoken = getSmarterCsrfToken();
          const url = submitButton.closest("form").getAttribute("action");
          const formData = new FormData(form);
          const context = {
            headers: {
              'Content-Type': 'multipart/form-data',
              "X-CSRFToken": csrftoken,
            }
          }

          // Check axios library docs: https://axios-http.com/docs/intro
          axios.post(url, formData, context)
            .then(function (response) {
              if (response) {
                form.reset();

                // Show message popup. For more info check the plugin's official documentation: https://sweetalert2.github.io/
                Swal.fire({
                  text: "Check your email. We just sent you a password reset link.",
                  icon: "success",
                  buttonsStyling: false,
                  confirmButtonText: "Dismiss",
                  customClass: {
                    confirmButton: "btn btn-primary",
                  },
                }).then(() => {
                  const redirectUrl = form.getAttribute("data-kt-redirect-url");
                  if (redirectUrl) {
                    location.href = redirectUrl;
                  }
                });
              } else {
                // Show error popup. For more info check the plugin's official documentation: https://sweetalert2.github.io/
                Swal.fire({
                  text: "Sorry, the email is incorrect, please try again.",
                  icon: "error",
                  buttonsStyling: false,
                  confirmButtonText: "Ok, got it!",
                  customClass: {
                    confirmButton: "btn btn-primary",
                  },
                });
              }
            })
            .catch(function (error) {
              Swal.fire({
                text: "Sorry, looks like there are some errors detected, please try again.",
                icon: "error",
                buttonsStyling: false,
                confirmButtonText: "Ok, got it!",
                customClass: {
                  confirmButton: "btn btn-primary",
                },
              });
            })
            .then(() => {
              // Hide loading indication
              submitButton.removeAttribute("data-kt-indicator");

              // Enable button
              submitButton.disabled = false;
            });
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

  // Public Functions
  return {
    // public functions
    init: function () {
      form = document.querySelector("#kt_password_reset_form");
      submitButton = document.querySelector("#kt_password_reset_submit");
      handleForm();
      handleSubmitAjax(); // use for ajax submit
    },
  };
})();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  KTAuthResetPassword.init();
});
