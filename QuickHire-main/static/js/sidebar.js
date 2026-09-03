(function () {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });
    }

    const profileTrigger = document.getElementById('profile-dropdown-trigger');
    const profileDropdown = document.getElementById('profile-dropdown');
    const profileWrap = profileTrigger && profileDropdown ? profileTrigger.closest('.profile-dropdown-wrap') : null;
    if (profileTrigger && profileDropdown && profileWrap) {
        profileTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = profileWrap.classList.toggle('is-open');
            profileTrigger.setAttribute('aria-expanded', isOpen);
            profileDropdown.setAttribute('aria-hidden', !isOpen);
        });
        document.addEventListener('click', () => {
            profileWrap.classList.remove('is-open');
            profileTrigger.setAttribute('aria-expanded', 'false');
            profileDropdown.setAttribute('aria-hidden', 'true');
        });
    }

    if (typeof feather !== 'undefined') {
        feather.replace();
    }
})();
