// Lawrence McDaniel -- https://lawrencemcdaniel.com
// Jan-2025
// manage active class on menu items



"use strict";

// On document ready
KTUtil.onDOMContentLoaded(function() {

  const menuItems = document.querySelectorAll('.menu-item');

  menuItems.forEach(item => {
      item.addEventListener('click', function() {
          // Remove 'active' class from all menu links
          document.querySelectorAll('.menu-link.active').forEach(link => {
              link.classList.remove('active');
          });

          // Add 'active' class to the clicked menu link
          const menuLink = item.querySelector('.menu-link');
          if (menuLink) {
              menuLink.classList.add('active');
          }
      });
  });

});
