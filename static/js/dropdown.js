/* ResumeMaker User Menu Dropdown Functionality */

function toggleUserDropdown(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  const menu = document.getElementById('userDropdownMenu');
  if (menu) {
    menu.classList.toggle('show');
  }
}

// Close dropdown on outside click
document.addEventListener('click', function(event) {
  const menu = document.getElementById('userDropdownMenu');
  const trigger = document.querySelector('.dropdown-trigger');
  
  if (menu && menu.classList.contains('show')) {
    if (!menu.contains(event.target) && (!trigger || !trigger.contains(event.target))) {
      menu.classList.remove('show');
    }
  }
});

// Close dropdown on Escape key
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    const menu = document.getElementById('userDropdownMenu');
    if (menu && menu.classList.contains('show')) {
      menu.classList.remove('show');
    }
  }
});
