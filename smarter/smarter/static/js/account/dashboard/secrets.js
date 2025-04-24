"use strict";

// Class definition
var KTAccountSecrets = function () {
    // Private variables
    var sandboxCheckBox;
    var sandboxLabel;
    var sandboxNotice;
    var buttonSecretDelete;
    var buttonSecretEdit;
    var primaryKey;

    function handleDelete(button) {

      button.attr("data-kt-indicator", "on");
      button.prop("disabled", true);
      primaryKey = button.data('record-id');
      const url = "/account/dashboard/secrets/" + primaryKey + "/";

      const csrfToken = getSmarterCsrfToken();
      const context = {
        headers: {
          'Content-Type': 'application/json',
          "X-CSRFToken": csrfToken,
        }
      }

      console.log('context', context);

      axios
      .delete(url, context)
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

    function handleEdit(button) {

      primaryKey = button.data('record-id');
      const url = "/account/dashboard/secrets/" + primaryKey + "/";
      window.location.href = url;
    }

    // Private functions
    var initSecretDelete = function() {
      buttonSecretDelete.click(function() {
        var recordId = $(this).data('record-id');
        console.log('buttonSecretDelete clicked', 'Record ID:', recordId);
        handleDelete($(this));
      });
    }
    var initSecretEdit = function() {
      buttonSecretEdit.click(function() {
        var recordId = $(this).data('record-id');
        console.log('buttonSecretEdit clicked', 'Record ID:', recordId);
        handleEdit($(this));
      });
    }

    // Public methods
    return {
        init: function () {
          sandboxCheckBox = $('#input_sandbox_mode_checkbox');
          sandboxLabel = $('#label_sandbox_mode');
          sandboxNotice = $('#notice_sandbox_mode');
          buttonSecretDelete = $('.button_secret_delete');
          buttonSecretEdit = $('.button_secret_edit');

          sandboxCheckBox.click(function() {
            var sandboxMode = sandboxCheckBox.is(':checked');
            if (sandboxMode) {
              sandboxLabel.text('Live Mode');
              sandboxNotice.attr('style', 'display: none !important');
            }
            else {
              sandboxLabel.text('Sandbox Mode');
              sandboxNotice.attr('style', 'display: block !important');
            }

          });

          initSecretEdit();
          initSecretDelete();
        }
    }
}();

// On document ready
KTUtil.onDOMContentLoaded(function() {
    KTAccountSecrets.init();
});
