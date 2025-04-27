"use strict";

// Class definition
var KTAccountSecret = (function () {
  // Private variables
  var form;
  var primaryKey;
  var buttonSecretCopy;
  var saveButton;
  var cancelButton;
  var inputSecret;
  var validation;


  // Private functions
  var initValidation = function () {
      // Init form validation rules. For more info check the FormValidation plugin's official documentation:https://formvalidation.io/
      validation = FormValidation.formValidation(
          form,
          {
              fields: {
                  description: {
                      validators: {
                          notEmpty: {
                              message: 'Description is required'
                          }
                      }
                  },
                  value: {
                    validators: {
                        notEmpty: {
                            message: 'Value is required'
                        }
                    }
                },
            },
              plugins: {
                  trigger: new FormValidation.plugins.Trigger(),
                  saveButton: new FormValidation.plugins.SubmitButton(),
                  defaultSubmit: new FormValidation.plugins.DefaultSubmit(), // Uncomment this line to enable normal button submit after form validation
                  // bootstrap: new FormValidation.plugins.Bootstrap5({
                  //     rowSelector: '.fv-row',
                  //     eleInvalidClass: '',
                  //     eleValidClass: ''
                  // })
              }
          }
      );

      // Select2 validation integration
      $(form.querySelector('[name="description"]')).on('change', function() {
          validation.revalidateField('description');
      });

  }

  var initSecretCopy = function () {


    buttonSecretCopy.click(function () {

      if (window.location.protocol === "https:") {
        // Use Clipboard API when page is served over HTTPS
        navigator.clipboard.writeText(inputSecret.val()).then(
          function () {
            Swal.fire({
              text: "Copied Secret to the clipboard.",
              icon: "success",
              confirmButtonText: "Ok",
              buttonsStyling: false,
              customClass: {
                confirmButton: "btn btn-light-primary",
              },
            });
          },
          function (err) {
            console.error("Could not copy secret: ", err);
          },
        );
      } else {
        // Fallback to document.execCommand for non-HTTPS (development)
        var text = inputSecret.val();
        var textarea = document.createElement("textarea");
        textarea.textContent = text;
        textarea.style.position = "fixed"; // Prevent scrolling to bottom of page in MS Edge.
        document.body.appendChild(textarea);
        textarea.select();

        try {
          document.execCommand("copy");
          Swal.fire({
            text: "Copied Secret to the clipboard.",
            icon: "success",
            confirmButtonText: "Ok",
            buttonsStyling: false,
            customClass: {
              confirmButton: "btn btn-light-primary",
            },
          });
        } catch (ex) {
          swal.fire({
            text: "Sorry, looks like there are some errors detected, please try again.",
            icon: "error",
            buttonsStyling: false,
            confirmButtonText: "Ok, got it!",
            customClass: {
                confirmButton: "btn btn-light-primary"
            }
          });

        } finally {
          document.body.removeChild(textarea);
        }
      }
    });
  };

  var handleForm = function () {
    saveButton.on('click', function (e) {
      primaryKey = form.getAttribute('data-primary-key');

      e.preventDefault();
        validation.validate().then(function (status) {
          if (status == "Valid") {
            // Show loading indication
            saveButton.attr("data-kt-indicator", "on");

            // Disable button to avoid multiple click
            saveButton.prop("disabled", true);
            const csrftoken = getSmarterCsrfToken();
            const formData = new FormData(form);
            formData.delete('secret');

            // convert to json
            let object = {};
            formData.forEach((value, key) => object[key] = value);
            let json_body = JSON.stringify(object);

            // Log the entries in the FormData object
            for (let pair of formData.entries()) {
              console.log(pair[0]+ ', '+ pair[1]);
            }

            const url = primaryKey ? "/account/dashboard/secrets/" + primaryKey + "/" : "/account/dashboard/secrets/new/";
            const context = {
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken,
              }
            }

            // Check axios library docs: https://axios-http.com/docs/intro
            axios
              .patch(url, json_body, context)
              .then(function (response) {
                if (response) {
                  window.location.href = '/account/dashboard/secrets/';
                }
              })
              .catch(function (error) {
                Swal.fire({
                  text: error.response ? JSON.stringify(error.response.data) : 'An error occurred',
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
                saveButton.removeAttr("data-kt-indicator");

                // Enable button
                saveButton.prop("disabled", false);
              });
          }
        });
    });

    cancelButton.on('click', function (e) {
      window.location.href = '/account/dashboard/secrets/';
    });
}
// Public methods
  return {
    init: function () {
      form = document.getElementById('kt_secret_detail_form');
      saveButton = $(form).find('#kt_secret_form_save_btn');
      cancelButton = $(form).find('#kt_secret_form_cancel_btn');

      buttonSecretCopy = $(form).find('#button_secret_copy');
      inputSecret = $(form).find('#input_secret');

      initValidation();
      initSecretCopy();
      handleForm();
    },
  };
})();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  KTAccountSecret.init();
});
