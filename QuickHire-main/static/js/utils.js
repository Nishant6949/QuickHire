(function () {
    window.escapeHtml = function (str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    };

    window.scoreColorClass = function (score) {
        if (score >= 90) return 'green';
        if (score >= 70) return 'amber';
        return 'red';
    };
})();

// Dashboard page-load reveal animations
window.setupDashboardReveal = function () {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var revealEls = document.querySelectorAll('.stat-card, .card-panel, .data-table-wrap');
    revealEls.forEach(function (el, i) {
        el.setAttribute('data-reveal', 'up');
        if (i < 6) el.setAttribute('data-stagger', String((i % 4) + 1));
    });

    var observer = new IntersectionObserver(
        function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.08 }
    );

    document.querySelectorAll('[data-reveal]').forEach(function (el) {
        observer.observe(el);
    });
};

// Animated counter for stat values
window.animateCounter = function (el, targetValue, duration) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    duration = duration || 800;

    var rawText = String(targetValue);
    var suffix = rawText.replace(/[\d.]+/, '');
    var numericTarget = parseFloat(targetValue) || 0;
    if (isNaN(numericTarget) || numericTarget === 0) return;

    var start = performance.now();
    function update(now) {
        var elapsed = now - start;
        var progress = Math.min(elapsed / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = Math.round(numericTarget * eased);
        el.textContent = current + suffix;
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
};
