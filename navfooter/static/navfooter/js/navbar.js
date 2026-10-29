/**
 * GuardianTree FP — Master Navbar & Mobile Navigation Drawer Scripts
 */

(function () {
  const saved = localStorage.getItem('bf-theme');
  if (saved === 'light') {
    document.documentElement.removeAttribute('data-theme');
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  window.addEventListener('DOMContentLoaded', () => {
    syncThemeIcons();
  });
})();

function syncThemeIcons() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const icon = isDark ? '☀️' : '🌙';

  const dropdownIcon = document.getElementById('theme-icon-dropdown');
  if (dropdownIcon) dropdownIcon.textContent = icon;

  const mobileIcon = document.getElementById('mobile-theme-icon');
  if (mobileIcon) mobileIcon.textContent = icon;
}

let scrollTicking = false;
function handleNavbarScroll() {
  if (!scrollTicking) {
    window.requestAnimationFrame(function () {
      const wrapper = document.querySelector('.finance-navbar-wrapper');
      if (wrapper) {
        if (window.scrollY > 30) {
          wrapper.classList.add('scrolled');
        } else {
          wrapper.classList.remove('scrolled');
        }
      }
      scrollTicking = false;
    });
    scrollTicking = true;
  }
}
window.addEventListener('scroll', handleNavbarScroll, { passive: true });
window.addEventListener('DOMContentLoaded', handleNavbarScroll);

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  const nextTheme = isDark ? 'light' : 'dark';

  if (isDark) {
    html.removeAttribute('data-theme');
  } else {
    html.setAttribute('data-theme', 'dark');
  }
  localStorage.setItem('bf-theme', nextTheme);
  syncThemeIcons();
}

function toggleUserDropdown(event) {
  if (event) event.stopPropagation();
  const dropdown = document.getElementById('user-dropdown-menu');
  if (dropdown) {
    dropdown.classList.toggle('show');
  }
}

function toggleMobileDrawer(event) {
  if (event) event.stopPropagation();
  const drawer = document.getElementById('finance-mobile-drawer');
  const isOpen = drawer && drawer.classList.contains('open');

  if (isOpen) {
    closeMobileDrawer();
  } else {
    openMobileDrawer();
  }
}

function openMobileDrawer() {
  const drawer = document.getElementById('finance-mobile-drawer');
  const toggle = document.getElementById('finance-hamburger-toggle');
  const overlay = document.getElementById('finance-mobile-drawer-overlay');

  if (drawer) drawer.classList.add('open');
  if (toggle) toggle.classList.add('active');
  if (overlay) overlay.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeMobileDrawer() {
  const drawer = document.getElementById('finance-mobile-drawer');
  const toggle = document.getElementById('finance-hamburger-toggle');
  const overlay = document.getElementById('finance-mobile-drawer-overlay');

  if (drawer) drawer.classList.remove('open');
  if (toggle) toggle.classList.remove('active');
  if (overlay) overlay.classList.remove('show');
  document.body.style.overflow = '';
}

document.addEventListener('click', function (event) {
  const dropdown = document.getElementById('user-dropdown-menu');
  const trigger = document.getElementById('settings-dropdown-trigger');
  if (dropdown && dropdown.classList.contains('show')) {
    if (!dropdown.contains(event.target) && (!trigger || !trigger.contains(event.target))) {
      dropdown.classList.remove('show');
    }
  }
});

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape') {
    closeMobileDrawer();
    const dropdown = document.getElementById('user-dropdown-menu');
    if (dropdown) dropdown.classList.remove('show');
  }
});
