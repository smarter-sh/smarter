"use strict";

// Class definition
var KTModalNewAddress = function () {
	var submitButton;
	var cancelButton;
	var validator;
	var form;
	var modal;
	var modalEl;

	// Init form inputs
	var initAddressForm = function() {
		// Team assign. For more info, plase visit the official plugin site: https://select2.org/
        $(form.querySelector('[name="country"]')).select2().on('change', function() {
            // Revalidate the field when an option is chosen
            validator.revalidateField('country');
        });
	}

	// Handle form validation and submittion
	var handleAddressEdit = function() {
		// Stepper custom navigation

		// Init form validation rules. For more info check the FormValidation plugin's official documentation:https://formvalidation.io/
		validator = FormValidation.formValidation(
			form,
			{
				fields: {
					'first-name': {
						validators: {
							notEmpty: {
								message: gettext('First name is required')
							}
						}
					},
					'last-name': {
						validators: {
							notEmpty: {
								message: gettext('Last name is required')
							}
						}
					},
					'country': {
						validators: {
							notEmpty: {
								message: gettext('Country is required')
							}
						}
					},
					'address1': {
						validators: {
							notEmpty: {
								message: gettext('Address 1 is required')
							}
						}
					},
					'address2': {
						validators: {
							notEmpty: {
								message: gettext('Address 2 is required')
							}
						}
					},
					'city': {
						validators: {
							notEmpty: {
								message: gettext('City is required')
							}
						}
					},
					'state': {
						validators: {
							notEmpty: {
								message: gettext('State is required')
							}
						}
					},
					'postcode': {
						validators: {
							notEmpty: {
								message: gettext('Postcode is required')
							}
						}
					}
				},
				plugins: {
					trigger: new FormValidation.plugins.Trigger(),
					bootstrap: new FormValidation.plugins.Bootstrap5({
						rowSelector: '.fv-row',
                        eleInvalidClass: '',
                        eleValidClass: ''
					})
				}
			}
		);

		// Action buttons
		submitButton.addEventListener('click', function (e) {
			e.preventDefault();

			// Validate form before submit
			if (validator) {
				validator.validate().then(function (status) {
					console.log('validated!');

					if (status == 'Valid') {
						submitButton.setAttribute('data-kt-indicator', 'on');

						// Disable button to avoid multiple click
						submitButton.disabled = true;

						// Simulate ajax process
						setTimeout(function() {
							submitButton.removeAttribute('data-kt-indicator');

							// Enable button
							submitButton.disabled = false;

							// Show success message.  For more info check the plugin's official documentation: https://sweetalert2.github.io/
							Swal.fire({
								text: gettext("Form has been successfully submitted!"),
								icon: "success",
								buttonsStyling: false,
								confirmButtonText: gettext("Ok, got it!"),
								customClass: {
									confirmButton: "btn btn-primary"
								}
							}).then(function (result) {
								if (result.isConfirmed) {
									modal.hide();
								}
							});

							//form.submit(); // Submit form
						}, 2000);
					} else {
						// Show error message.
						Swal.fire({
							text: gettext("Sorry, looks like there are some errors detected, please try again."),
							icon: "error",
							buttonsStyling: false,
							confirmButtonText: gettext("Ok, got it!"),
							customClass: {
								confirmButton: "btn btn-primary"
							}
						});
					}
				});
			}
		});

		cancelButton.addEventListener('click', function (e) {
			e.preventDefault();

			Swal.fire({
				text: gettext("Are you sure you would like to cancel?"),
				icon: "warning",
				showCancelButton: true,
				buttonsStyling: false,
				confirmButtonText: gettext("Yes, cancel it!"),
				cancelButtonText: gettext("No, return"),
				customClass: {
					confirmButton: "btn btn-primary",
					cancelButton: "btn btn-active-light"
				}
			}).then(function (result) {
				if (result.value) {
					form.reset(); // Reset form
					modal.hide(); // Hide modal
				} else if (result.dismiss === 'cancel') {
					Swal.fire({
						text: gettext("Your form has not been cancelled!."),
						icon: "error",
						buttonsStyling: false,
						confirmButtonText: gettext("Ok, got it!"),
						customClass: {
							confirmButton: "btn btn-primary",
						}
					});
				}
			});
		});
	}

  var handleAddressDelete = function() {
    KTUtil.on(document.body,  '[data-kt-billing-action="address-delete"]', 'click', function(e) {
        e.preventDefault();

        var el = this;

        swal.fire({
            text: gettext("Are you sure you would like to delete selected address ?"),
            icon: "warning",
            buttonsStyling: false,
            showDenyButton: true,
            confirmButtonText: gettext("Yes"),
            denyButtonText: 'No',
            customClass: {
                confirmButton: "btn btn-primary",
                denyButton: "btn btn-light-danger"
            }
        }).then((result) => {
            if (result.isConfirmed) {
                el.setAttribute('data-kt-indicator', 'on');
                el.disabled = true;

                setTimeout(function() {
                    Swal.fire({
                        text: gettext('Your selected address has been successfully deleted'),
                        icon: 'success',
                        confirmButtonText: gettext("Ok"),
                        buttonsStyling: false,
                        customClass: {
                            confirmButton: "btn btn-light-primary"
                        }
                    }).then((result) => {
                        el.closest('[data-kt-billing-element="address"]').remove();
                    });
                }, 2000);
            }
        });
    });
  }


	return {
		// Public functions
		init: function () {
			// Elements
			modalEl = document.querySelector('#kt_modal_new_address');

			if (!modalEl) {
				return;
			}

			modal = new bootstrap.Modal(modalEl);

			form = document.querySelector('#kt_modal_new_address_form');
			submitButton = document.getElementById('kt_modal_new_address_submit');
			cancelButton = document.getElementById('kt_modal_new_address_cancel');

			initAddressForm();
			handleAddressEdit();
      handleAddressDelete();

		}
	};
}();

// On document ready
KTUtil.onDOMContentLoaded(function () {
  console.log("billing-address.js - KTUtil.onDOMContentLoaded")
	KTModalNewAddress.init();
});
