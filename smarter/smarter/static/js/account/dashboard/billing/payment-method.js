"use strict";

// Class definition
var KTModalPaymentMethod = (function () {
  var editButtons;
  var submitButton;
  var cancelButton;
  var validator;
  var form;
  var modal;
  var modalEl;

  // Init form event handlers
  var initModule = function () {
    // Expiry month. For more info, please visit the official plugin site: https://select2.org/
    $(form.querySelector('[name="card_expiry_month"]')).on(
      "change",
      function () {
        // Revalidate the field when an option is chosen
        validator.revalidateField("card_expiry_month");
      },
    );

    // Expiry year. For more info, please visit the official plugin site: https://select2.org/
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
            const csrfToken = getSmarterCsrfToken();
            const url = submitButton.closest("form").getAttribute("action");
            const formData = new FormData(form);
            const context = {
              headers: {
                "Content-Type": "multipart/form-data",
                "X-CSRFToken": csrfToken,
              },
            };

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
              text: "Please correct the following errors and try again.",
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

    editButtons.forEach((button) => {
      button.addEventListener("click", function (e) {
        console.log("edit button clicked");
        var myModal = new bootstrap.Modal(
          document.getElementById("kt_modal_payment_method"),
        );
        var modalTitle = document.getElementById(
          "kt_modal_payment_method_title",
        );
        var billingId = this.getAttribute("data-kt-billing-id");
        modalTitle.innerHTML = "Edit Payment Method: " + billingId;

        const csrfToken = getSmarterCsrfToken();
        const url =
          "/account/dashboard/billing/payment-methods/" + billingId + "/";
        const context = {
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
        };

        // Check axios library docs: https://axios-http.com/docs/intro
        axios
          .get(url, context)
          .then(function (response) {
            if (response) {
              console.log("response", response);

              let card_name = document.querySelector('input[name="card_name"]');
              card_name.value = response.data.card_name;

              let card_number = document.querySelector('input[name="card_number"]');
              card_number.value = response.data.card_number;

              let card_expiration_month = document.querySelector('select[name="card_expiration_month"]');
              let optionsMonth = card_expiration_month.options;
              console.log("response.data.card_expiration_month", response.data.card_expiration_month);
              let expirationMonth = response.data.card_expiration_month;

              for(let option of optionsMonth) {
                if(option.value == expirationMonth) {
                  option.selected = true;
                  break;
                }
              }

              $(card_expiration_month).trigger('change');



              let card_expiration_year = document.querySelector('select[name="card_expiration_year"]');
              let optionsYear = card_expiration_year.options;
              console.log("response.data.card_expiration_year", response.data.card_expiration_year);
              let expirationYear = response.data.card_expiration_year;

              for(let option of optionsYear) {
                if(option.value == expirationYear) {
                  option.selected = true;
                  break;
                }
              }

              $(card_expiration_year).trigger('change');

              let card_cvc = document.querySelector('input[name="card_cvc"]');
              card_cvc.value = response.data.card_cvc;


              myModal.show();
              // Remove loading indication
              button.removeAttribute("data-kt-indicator");

              // Enable button
              button.disabled = true;
            } else {
              // Show error popup. For more info check the plugin's official documentation: https://sweetalert2.github.io/
              Swal.fire({
                text: "Hmmmm, please try again.",
                icon: "error",
                buttonsStyling: false,
                confirmButtonText: "Dismiss",
                customClass: {
                  confirmButton: "btn btn-primary",
                },
              });
            }
          })
          .catch(function (error) {
            console.log("error", error);
            Swal.fire({
              text: "Sorry, looks like the server couldn't process your request. Please try again.",
              icon: "error",
              buttonsStyling: false,
              confirmButtonText: "Dismiss",
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
      });
    });
  };

  var handleCardDelete = function () {
    KTUtil.on(
      document.body,
      '[data-kt-billing-action="payment-method-delete"]',
      "click",
      function (e) {
        e.preventDefault();

        var el = this;
        var billingId = el.getAttribute("data-kt-billing-id");

        const csrfToken = getSmarterCsrfToken();
        const url =
          "/account/dashboard/billing/payment-methods/" + billingId + "/";
        const context = {
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
        };

        swal
          .fire({
            text: "Delete this payment method?",
            icon: "warning",
            buttonsStyling: false,
            showDenyButton: true,
            confirmButtonText: "Yes",
            denyButtonText: "No",
            customClass: {
              confirmButton: "btn btn-primary",
              denyButton: "btn btn-light-danger",
            },
          })
          .then((result) => {
            if (result.isConfirmed) {
              el.setAttribute("data-kt-indicator", "on");
              el.disabled = true;

              // Check axios library docs: https://axios-http.com/docs/intro
              // delete the payment method
              // Check axios library docs: https://axios-http.com/docs/intro
              axios
                .delete(url, context)
                .then(function (response) {
                  if (response) {
                    // Remove loading indication
                    el.removeAttribute("data-kt-indicator");

                    // Enable button
                    el.disabled = false;

                    // Show popup confirmation
                    Swal.fire({
                      text: "Your selected card has been successfully deleted",
                      icon: "success",
                      confirmButtonText: "Ok",
                      buttonsStyling: false,
                      customClass: {
                        confirmButton: "btn btn-light-primary",
                      },
                    })
                      .catch((error) => {
                        Swal.fire({
                          text: "Sorry, looks like there are some errors detected, please try again.",
                          icon: "error",
                          confirmButtonText: "Ok",
                          buttonsStyling: false,
                          customClass: {
                            confirmButton: "btn btn-light-primary",
                          },
                        });
                      })
                      .then((result) => {
                        el.closest(
                          '[data-kt-billing-element="payment-method"]',
                        ).remove();
                      });
                  } else {
                    // Show error popup. For more info check the plugin's official documentation: https://sweetalert2.github.io/
                    Swal.fire({
                      text: "Oops.",
                      icon: "error",
                      buttonsStyling: false,
                      confirmButtonText: "Dismiss",
                      customClass: {
                        confirmButton: "btn btn-primary",
                      },
                    });
                  }
                })
                .then(() => {
                  // Hide loading indication
                  submitButton.removeAttribute("data-kt-indicator");

                  // Enable button
                  submitButton.disabled = false;
                });
            }
          });
      },
    );
  };

  return {
    // Public functions
    init: function () {
      // Elements
      modalEl = document.querySelector("#kt_modal_payment_method");

      if (!modalEl) {
        return;
      }

      editButtons = document.querySelectorAll(
        'button[data-kt-billing-action="payment-method-edit"]',
      );
      console.log("editButtons", editButtons);

      modal = new bootstrap.Modal(modalEl);

      form = document.querySelector("#kt_modal_payment_method_form");
      submitButton = document.getElementById("kt_modal_payment_method_submit");
      cancelButton = document.getElementById("kt_modal_payment_method_cancel");

      initModule();
      handleForm();
      handleCardDelete();
    },
  };
})();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  KTModalPaymentMethod.init();
});
