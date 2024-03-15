"use strict";

// Class definition
var KTAccountAPIKeys = function () {
    // Private variables
    var sandboxCheckBox;
    var sandboxLabel;
    var sandboxNotice;
    var buttonApiKeyActivate;
    var buttonApiKeyDeactivate;
    var buttonApiKeyDelete;
    var primaryKey;

    function handleAction(action, button) {
      console.log('handleAction: ', action);

      button.attr("data-kt-indicator", "on");
      button.prop("disabled", true);
      primaryKey = button.data('record-id');
      const url = "/account/dashboard/api-keys/" + primaryKey + "/";

      const csrfToken = getSmarterCsrfToken();
      console.log('csrfToken', csrfToken);
      const context = {
        headers: {
          'Content-Type': 'application/json',
          "X-CSRFToken": csrfToken,
        }
      }

      let jsonBody = {
        'action': action
      }

      axios
      .post(url, jsonBody, context)
      .then(function (response) {
        if (response) {
          console.log('response', response);
          window.location.reload();
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
        button.removeAttr("data-kt-indicator");
        button.prop("disabled", false);
      });

    }

    // Private functions
    var initAPIKeyCopy = function() {
        KTUtil.each(document.querySelectorAll('#kt_api_keys_table [data-action="copy"]'), function(button) {
            var tr = button.closest('tr');
            var license = KTUtil.find(tr, '[data-bs-target="license"]');

            var clipboard = new ClipboardJS(button, {
                target: license,
                text: function() {
                    return license.innerHTML;
                }
            });

            clipboard.on('success', function(e) {
                // Icons
                var copyIcon = button.querySelector('.ki-copy');
                var checkIcon = button.querySelector('.ki-check');

                // exit if check icon is already shown
                if (checkIcon) {
                   return;
                }

                // Create check icon
                checkIcon = document.createElement('i');
                checkIcon.classList.add('ki-solid');
                checkIcon.classList.add('ki-check');
                checkIcon.classList.add('fs-2');

                // Append check icon
                button.appendChild(checkIcon);

                // Highlight target
                license.classList.add('text-success');

                // Hide copy icon
                copyIcon.classList.add('d-none');

                // Set 3 seconds timeout to hide the check icon and show copy icon back
                setTimeout(function() {
                    // Remove check icon
                    copyIcon.classList.remove('d-none');
                    // Show check icon back
                    button.removeChild(checkIcon);

                    // Remove highlight
                    license.classList.remove('text-success');
                }, 3000);
            });
        });
    }
    var initAPIKeyActivate = function() {
      buttonApiKeyActivate.click(function() {
        console.log('buttonApiKeyActivate clicked');
        handleAction('activate', buttonApiKeyActivate);
      });
    }
    var initAPIKeyDeactivate = function() {
      buttonApiKeyDeactivate.click(function() {
        console.log('buttonApiKeyDeactivate clicked');
        handleAction('deactivate', buttonApiKeyDeactivate);
      });
    }
    var initAPIKeyDelete = function() {
      buttonApiKeyDelete.click(function() {
        console.log('buttonApiKeyDelete clicked');
        handleAction('delete', buttonApiKeyDelete);
      });
    }

    // Public methods
    return {
        init: function () {
          sandboxCheckBox = $('#input_sandbox_mode_checkbox');
          sandboxLabel = $('#label_sandbox_mode');
          sandboxNotice = $('#notice_sandbox_mode');
          buttonApiKeyActivate = $('#button_api_key_activate');
          buttonApiKeyDeactivate = $('#button_api_key_deactivate');
          buttonApiKeyDelete = $('#button_api_key_delete');

          sandboxCheckBox.click(function() {
            console.log('sandboxCheckBox clicked');
            var sandboxMode = sandboxCheckBox.is(':checked');
            if (sandboxMode) {
              sandboxLabel.text('Live Mode');
              sandboxNotice.attr('style', 'display: none !important');
            }
            else {
              sandboxLabel.text('Sandbox Mode');
              sandboxNotice.attr('style', 'display: block !important');
            }
            console.log('sandboxMode', sandboxMode);

          });

          initAPIKeyCopy();
          initAPIKeyActivate();
          initAPIKeyDeactivate();
          initAPIKeyDelete();
        }
    }
}();

// On document ready
KTUtil.onDOMContentLoaded(function() {
    console.log('KTAccountAPIKeys.init');
    KTAccountAPIKeys.init();
});
