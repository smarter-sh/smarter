"use strict";

// Class definition
var KTModalNewCard = (function () {
  var submitButton;
  var cancelButton;
  var validator;
  var form;
  var modal;
  var modalEl;

  // Init form inputsx
  var initForm = function () {
    // Expiry month. For more info, plase visit the official plugin site: https://select2.org/
    $(form.querySelector('[name="card_expiry_month"]')).on(
      "change",
      function () {
        // Revalidate the field when an option is chosen
        validator.revalidateField("card_expiry_month");
      },
    );

    // Expiry year. For more info, plase visit the official plugin site: https://select2.org/
    $(form.querySelector('[name="card_expiry_year"]')).on(
      "change",
      function () {
        // Revalidate the field when an option is chosen
        validator.revalidateField("card_expiry_year");
      },
    );
  };

  // Handle form validation and submittion
  var handleForm = function () {
    // Stepper custom navigation

    // Init form validation rules. For more info check the FormValidation plugin's official documentation:https://formvalidation.io/
    validator = FormValidation.formValidation(form, {
      fields: {
        card_name: {
          validators: {
            notEmpty: {
              message: "Name on card is required",
            },
          },
        },
        card_number: {
          validators: {
            notEmpty: {
              message: "Card member is required",
            },
            creditCard: {
              message: "Card number is not valid",
            },
          },
        },
        card_expiry_month: {
          validators: {
            notEmpty: {
              message: "Month is required",
            },
          },
        },
        card_expiry_year: {
          validators: {
            notEmpty: {
              message: "Year is required",
            },
          },
        },
        card_cvv: {
          validators: {
            notEmpty: {
              message: "CVV is required",
            },
            digits: {
              message: "CVV must contain only digits",
            },
            stringLength: {
              min: 3,
              max: 4,
              message: "CVV must contain 3 to 4 digits only",
            },
          },
        },
      },

      plugins: {
        trigger: new FormValidation.plugins.Trigger(),
        bootstrap: new FormValidation.plugins.Bootstrap5({
          rowSelector: ".fv-row",
          eleInvalidClass: "",
          eleValidClass: "",
        }),
      },
    });

    // Action buttons
    submitButton.addEventListener("click", function (e) {
      // Prevent default button action
      e.preventDefault();

      // Validate form before submit
      if (validator) {
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
            axios
              .post(url, formData, context)
              .then(function (response) {
                if (response) {
                  form.reset();
                  // Remove loading indication
                  submitButton.removeAttribute("data-kt-indicator");

                  // Enable button
                  submitButton.disabled = false;

                  // Show popup confirmation
                  Swal.fire({
                    text: "New payment method saved.",
                    icon: "success",
                    buttonsStyling: false,
                    confirmButtonText: "Ok",
                    customClass: {
                      confirmButton: "btn btn-primary",
                    },
                  }).then(function (result) {
                    if (result.isConfirmed) {
                      modal.hide();
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
      }
    });

    cancelButton.addEventListener("click", function (e) {
      e.preventDefault();

      // Show success message. For more info check the plugin's official documentation: https://sweetalert2.github.io/
      Swal.fire({
        text: "Are you sure you want to cancel?",
        icon: "warning",
        showCancelButton: true,
        buttonsStyling: false,
        confirmButtonText: "Yes",
        cancelButtonText: "No, return",
        customClass: {
          confirmButton: "btn btn-primary",
          cancelButton: "btn btn-active-light",
        },
      }).then(function (result) {
        if (result.value) {
          form.reset(); // Reset form
          modal.hide(); // Hide modal
        } else if (result.dismiss === "cancel") {
          // Show error message.
          Swal.fire({
            text: "Your form has not been cancelled!.",
            icon: "error",
            buttonsStyling: false,
            confirmButtonText: "Ok",
            customClass: {
              confirmButton: "btn btn-primary",
            },
          });
        }
      });
    });
  };

  return {
    // Public functions
    init: function () {
      // Elements
      modalEl = document.querySelector("#kt_modal_new_card");

      if (!modalEl) {
        return;
      }

      modal = new bootstrap.Modal(modalEl);

      form = document.querySelector("#kt_modal_new_card_form");
      submitButton = document.getElementById("kt_modal_new_card_submit");
      cancelButton = document.getElementById("kt_modal_new_card_cancel");

      initForm();
      handleForm();
    },
  };
})();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  KTModalNewCard.init();
});
