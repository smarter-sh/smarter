$(document).ready(function(){
  Swal.fire({
      text: "We have received your request. You will be notified once we go live.",
      icon: "success",
      buttonsStyling: false,
      confirmButtonText: "Dismiss",
      customClass: {
          confirmButton: "btn btn-primary"
      }
  }).then(function (result) {
    // more stuff.
  });

});
