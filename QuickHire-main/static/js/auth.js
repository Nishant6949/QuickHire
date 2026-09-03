document.addEventListener('DOMContentLoaded', () => {
    if (window.feather) feather.replace();

    const wrapper = document.getElementById('login-password-wrapper');
    const input = document.getElementById('login-password');
    const toggle = document.getElementById('login-password-toggle');
    if (wrapper && input && toggle) {
        toggle.addEventListener('click', () => {
            const isVisible = wrapper.classList.toggle('is-visible');
            input.type = isVisible ? 'text' : 'password';
        });
    }
});
