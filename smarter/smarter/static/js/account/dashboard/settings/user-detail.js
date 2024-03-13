"use strict";

// Class definition
var KTAccountDetails = function () {
    // Private variables
    var form;
    var primaryKey;
    var editButton;
    var saveButton;
    var cancelButton;
    var validation;

    function toggleFormReadonly(isReadonly) {
      var inputs = form.querySelectorAll('input, textarea');
      var selects = form.querySelectorAll('select');

      for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].id === 'input_account_number') {
          inputs[i].readOnly = true;
        } else {
          inputs[i].readOnly = isReadonly;
        }
      }

      for (var i = 0; i < selects.length; i++) {
          selects[i].disabled = isReadonly;
      }

      if (isReadonly) {
        saveButton.hide();
        cancelButton.hide();
      } else {
        saveButton.show();
        cancelButton.show();
      }
    }

    // Private functions
    var initValidation = function () {
        // Init form validation rules. For more info check the FormValidation plugin's official documentation:https://formvalidation.io/
        validation = FormValidation.formValidation(
            form,
            {
                fields: {
                    fname: {
                        validators: {
                            notEmpty: {
                                message: 'First name is required'
                            }
                        }
                    },
                    lname: {
                        validators: {
                            notEmpty: {
                                message: 'Last name is required'
                            }
                        }
                    },
                    company: {
                        validators: {
                            notEmpty: {
                                message: 'Company name is required'
                            }
                        }
                    },
                    phone: {
                        validators: {
                            notEmpty: {
                                message: 'Contact phone number is required'
                            }
                        }
                    },
                    country: {
                        validators: {
                            notEmpty: {
                                message: 'Please select a country'
                            }
                        }
                    },
                    timezone: {
                        validators: {
                            notEmpty: {
                                message: 'Please select a timezone'
                            }
                        }
                    },
                    'communication[]': {
                        validators: {
                            notEmpty: {
                                message: 'Please select at least one communication method'
                            }
                        }
                    },
                    language: {
                        validators: {
                            notEmpty: {
                                message: 'Please select a language'
                            }
                        }
                    },
                },
                plugins: {
                    trigger: new FormValidation.plugins.Trigger(),
                    saveButton: new FormValidation.plugins.SubmitButton(),
                    //defaultSubmit: new FormValidation.plugins.DefaultSubmit(), // Uncomment this line to enable normal button submit after form validation
                    bootstrap: new FormValidation.plugins.Bootstrap5({
                        rowSelector: '.fv-row',
                        eleInvalidClass: '',
                        eleValidClass: ''
                    })
                }
            }
        );

        // Select2 validation integration
        $(form.querySelector('[name="country"]')).on('change', function() {
            // Revalidate the color field when an option is chosen
            validation.revalidateField('country');
        });

        $(form.querySelector('[name="language"]')).on('change', function() {
            // Revalidate the color field when an option is chosen
            validation.revalidateField('language');
        });

        $(form.querySelector('[name="timezone"]')).on('change', function() {
            // Revalidate the color field when an option is chosen
            validation.revalidateField('timezone');
        });
    }

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
                formData.delete('is_staff');

                var is_staff = form.querySelector('#input_is_staff');
                if (is_staff.checked) {
                  formData.append('is_staff', 'True');
                } else {
                  formData.append('is_staff', 'False');
                }
                const url = "/account/dashboard/users/" + primaryKey + "/";
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
                      toggleFormReadonly(true);
                    }
                  })
                  .catch(function (error) {
                    Swal.fire({
                      text: JSON.stringify(error.response.data),
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
    }

    // Public methods
    return {
        init: function () {
            form = document.getElementById('kt_user_detail_form');
            editButton = $('#kt_user_form_edit_btn');
            saveButton = $(form).find('#kt_user_form_save_btn');
            cancelButton = $(form).find('#kt_user_form_cancel_btn');

            function initForm() {
                location.reload();
            }
              window.onload = function() {
                    toggleFormReadonly(true);
              }
              cancelButton.click(function() {
                  toggleFormReadonly(true);
                  initForm();
              });

              editButton.click(function() {
                toggleFormReadonly(false);
              });

              initValidation();
              handleForm();
        }
    }
}();


// On document ready
KTUtil.onDOMContentLoaded(function() {
    KTAccountDetails.init();
});
