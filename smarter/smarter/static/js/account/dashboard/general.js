"use strict";

// Class definition
var KTProfileGeneral = function () {

// Add event listener to each navigation link
document.querySelectorAll('.nav-item a').forEach(function(link) {
  link.addEventListener('click', function () {
      // Store the clicked link's pathname in local storage
      localStorage.setItem('activeLink', this.pathname);
  });
});

// Add 'active' class to the link that matches the pathname stored in local storage
window.addEventListener('DOMContentLoaded', (event) => {
  var activeLink = localStorage.getItem('activeLink');

  document.querySelectorAll('.nav-item a').forEach(function(link) {
      if (link.pathname === activeLink) {
          link.classList.add('active');
      } else {
          link.classList.remove('active');
      }
  });
});

  // Public methods
    return {
        init: function () {
        }
    }
}();

// On document ready
KTUtil.onDOMContentLoaded(function() {
    KTProfileGeneral.init();
});
