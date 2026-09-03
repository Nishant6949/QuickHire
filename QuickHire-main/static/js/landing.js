document.addEventListener('DOMContentLoaded', () => {
    if (window.feather) feather.replace();
    setupFeaturesCarousel();
    setupSmoothScroll();
    setupMobileNav();
    setupScrollReveal();
    setupNavbarScroll();
});

function setupMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const menu = document.querySelector('.nav-left');
    const body = document.body;
    if (!toggle || !menu) return;

    function openMenu() {
        toggle.setAttribute('aria-expanded', 'true');
        toggle.setAttribute('aria-label', 'Close menu');
        menu.classList.add('nav-menu-open');
        body.classList.add('nav-overlay-open');
    }

    function closeMenu() {
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', 'Open menu');
        menu.classList.remove('nav-menu-open');
        body.classList.remove('nav-overlay-open');
    }

    function isOpen() {
        return menu.classList.contains('nav-menu-open');
    }

    toggle.addEventListener('click', () => {
        if (isOpen()) closeMenu();
        else openMenu();
    });

    menu.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => closeMenu());
    });

    window.addEventListener('resize', () => {
        if (window.matchMedia('(min-width: 769px)').matches && isOpen()) closeMenu();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen()) closeMenu();
    });
}

function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (!target) return;
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

function setupFeaturesCarousel() {
    const section = document.querySelector('.features-section');
    const track = document.querySelector('.features-track');
    const wrap = document.querySelector('.features-carousel');
    if (!section || !track || !wrap) return;

    const cards = track.querySelectorAll('.feature-card');
    const count = cards.length;
    if (count === 0) return;

    const mobileQuery = window.matchMedia('(max-width: 768px)');
    function isMobile() {
        return mobileQuery.matches;
    }

    let currentIndex = 0;
    let cachedMaxIndex = 0;
    let sectionInView = false;

    function checkSectionInMiddle() {
        const rect = section.getBoundingClientRect();
        const sectionCenterY = rect.top + rect.height / 2;
        const viewportMiddleStart = window.innerHeight * 0.25;
        const viewportMiddleEnd = window.innerHeight * 0.75;
        const inMiddle = sectionCenterY >= viewportMiddleStart && sectionCenterY <= viewportMiddleEnd;
        if (inMiddle !== sectionInView) {
            sectionInView = inMiddle;
            updateActiveCard();
        }
    }

    window.addEventListener('scroll', () => {
        checkSectionInMiddle();
    }, { passive: true });
    const observer = new IntersectionObserver(
        () => checkSectionInMiddle(),
        { threshold: [0, 0.25, 0.5, 0.75, 1], rootMargin: '0px' }
    );
    observer.observe(section);
    checkSectionInMiddle();

    function getMaxIndex() {
        const cardHeight = cards[0].offsetHeight;
        const gap = parseFloat(getComputedStyle(track).gap) || 24;
        const step = cardHeight + gap;
        const maxScroll = Math.max(0, wrap.scrollHeight - wrap.clientHeight);
        return maxScroll <= 0 ? 0 : Math.min(count - 1, Math.round(maxScroll / step));
    }

    function goToSlide(index, animate = true) {
        currentIndex = Math.max(0, Math.min(index, cachedMaxIndex));

        const card = cards[currentIndex];
        if (card) {
            const cardTop = card.offsetTop;
            const cardHeight = card.offsetHeight;
            const wrapHeight = wrap.clientHeight;
            const maxScroll = wrap.scrollHeight - wrapHeight;
            const top = Math.max(0, Math.min(maxScroll, cardTop - wrapHeight / 2 + cardHeight / 2));
            wrap.scrollTo({ top, behavior: animate ? 'smooth' : 'auto' });
        }

        updateActiveCard();
    }

    function updateActiveCard() {
        cards.forEach((card, i) => card.classList.toggle('active', sectionInView && i === currentIndex));
    }

    let wheelCooldown = false;
    document.addEventListener('wheel', (e) => {
        if (!sectionInView) return;
        const delta = e.deltaY;
        if (Math.abs(delta) < 5) return;
        const scrollingDown = delta > 0;
        const atStart = currentIndex === 0;
        const atEnd = currentIndex >= cachedMaxIndex;
        if (scrollingDown && atEnd) return;
        if (!scrollingDown && atStart) return;
        e.preventDefault();
        if (wheelCooldown) return;
        wheelCooldown = true;
        setTimeout(() => { wheelCooldown = false; }, 400);
        goToSlide(currentIndex + (scrollingDown ? 1 : -1));
    }, { passive: false });

    let scrollSyncRaf = null;
    function syncIndexFromScroll() {
        if (!cards.length) return;
        if (scrollSyncRaf !== null) return;
        scrollSyncRaf = requestAnimationFrame(() => {
            scrollSyncRaf = null;
            const wrapRect = wrap.getBoundingClientRect();
            const wrapCenterY = wrapRect.top + wrapRect.height / 2;
            let best = 0;
            let bestDist = Infinity;
            cards.forEach((card, i) => {
                const r = card.getBoundingClientRect();
                const centerY = r.top + r.height / 2;
                const dist = Math.abs(centerY - wrapCenterY);
                if (dist < bestDist) {
                    bestDist = dist;
                    best = i;
                }
            });
            if (best !== currentIndex) {
                currentIndex = best;
                updateActiveCard();
            }
        });
    }

    wrap.addEventListener('scroll', () => syncIndexFromScroll(), { passive: true });

    let touchStartY = 0;
    let touchGestureHandled = false;
    const teamSection = document.querySelector('#team');
    document.addEventListener('touchstart', (e) => {
        if (!isMobile()) return;
        touchStartY = e.touches[0].clientY;
        touchGestureHandled = false;
    }, { passive: true });
    document.addEventListener('touchmove', (e) => {
        if (!isMobile() || !sectionInView) return;
        const touchY = e.touches[0].clientY;
        const deltaY = touchStartY - touchY;
        const threshold = 50;
        const atStart = currentIndex === 0;
        const atEnd = currentIndex >= cachedMaxIndex;
        if (deltaY > threshold && !touchGestureHandled) {
            if (atEnd && teamSection) {
                e.preventDefault();
                touchGestureHandled = true;
                teamSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else if (!atEnd) {
                e.preventDefault();
                touchGestureHandled = true;
                goToSlide(currentIndex + 1);
            }
        } else if (deltaY < -threshold && !touchGestureHandled) {
            if (!atStart) {
                e.preventDefault();
                touchGestureHandled = true;
                goToSlide(currentIndex - 1);
            }
        } else if (touchGestureHandled) {
            e.preventDefault();
        }
    }, { passive: false });

    function init() {
        requestAnimationFrame(() => {
            cachedMaxIndex = getMaxIndex();
            goToSlide(0, false);
        });
    }
    init();
    window.addEventListener('resize', () => {
        cachedMaxIndex = getMaxIndex();
        goToSlide(Math.min(currentIndex, cachedMaxIndex), false);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// SCROLL REVEAL SYSTEM
// Uses IntersectionObserver to reveal elements as they scroll into view.
// Hero section is excluded — it has its own CSS slideUp animation.
// ─────────────────────────────────────────────────────────────────────────────
function setupScrollReveal() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var revealConfig = [
        { selector: '.features-headline', reveal: 'up' },
        { selector: '.features-description', reveal: 'up', stagger: 1 },
        { selector: '.features-carousel-wrap', reveal: 'right' },
        { selector: '.team-label', reveal: 'up' },
        { selector: '.section-title', reveal: 'up', stagger: 1 },
        { selector: '.team-card', reveal: 'up', staggerEach: true },
        { selector: '.footer', reveal: 'up' },
    ];

    revealConfig.forEach(function (cfg) {
        var elements = document.querySelectorAll(cfg.selector);
        elements.forEach(function (el, i) {
            // Skip elements already visible on load (above fold)
            var rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight * 0.85) return;

            el.setAttribute('data-reveal', cfg.reveal);
            if (cfg.stagger) el.setAttribute('data-stagger', cfg.stagger);
            if (cfg.staggerEach) el.setAttribute('data-stagger', String(i + 1));
        });
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
        { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    document.querySelectorAll('[data-reveal]').forEach(function (el) {
        observer.observe(el);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// NAVBAR SCROLL STATE
// Adds .is-scrolled class to navbar when page is scrolled, for elevated shadow.
// ─────────────────────────────────────────────────────────────────────────────
function setupNavbarScroll() {
    var navbar = document.querySelector('.navbar');
    if (!navbar) return;

    var ticking = false;
    window.addEventListener('scroll', function () {
        if (!ticking) {
            requestAnimationFrame(function () {
                navbar.classList.toggle('is-scrolled', window.scrollY > 20);
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
}
