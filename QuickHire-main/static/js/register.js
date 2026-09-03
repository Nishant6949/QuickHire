document.addEventListener('DOMContentLoaded', () => {
    if (window.feather) feather.replace();

    function setupPasswordToggle(wrapperId, inputId, toggleId) {
        const wrapper = document.getElementById(wrapperId);
        const input = document.getElementById(inputId);
        const toggle = document.getElementById(toggleId);
        if (wrapper && input && toggle) {
            toggle.addEventListener('click', () => {
                const isVisible = wrapper.classList.toggle('is-visible');
                input.type = isVisible ? 'text' : 'password';
            });
        }
    }
    setupPasswordToggle('password-wrapper', 'password', 'password-toggle');
    setupPasswordToggle('confirm-password-wrapper', 'confirm-password', 'confirm-password-toggle');
});
