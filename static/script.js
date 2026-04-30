// ================================
// SLIDER MODERNO (FULL WIDTH)
// ================================
class Slider {
    constructor(container, wrapper) {
        this.container = container;
        this.wrapper = wrapper;
        this.slides = wrapper.querySelectorAll('.slide');
        this.current = 0;
        this.autoplay = null;
        this.interval = 6000;
        this.isTransitioning = false;
        this.progress = container.querySelector('.slider-progress');

        this.prevBtn = container.querySelector('.prev');
        this.nextBtn = container.querySelector('.next');

        this.init();
    }

    init() {
        if (this.prevBtn && this.nextBtn) {
            this.prevBtn.addEventListener('click', () => this.move(-1));
            this.nextBtn.addEventListener('click', () => this.move(1));
        }

        const dots = this.container.querySelectorAll('.dot');
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => this.go(index));
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') this.move(-1);
            if (e.key === 'ArrowRight') this.move(1);
        });

        this.setupTouch();
        this.container.addEventListener('mouseenter', () => this.pause());
        this.container.addEventListener('mouseleave', () => this.startAutoplay());

        this.startAutoplay();
    }

    move(direction) {
        if (this.isTransitioning) return;
        this.isTransitioning = true;

        this.current += direction;
        if (this.current >= this.slides.length) this.current = 0;
        if (this.current < 0) this.current = this.slides.length - 1;
        this.update();
        this.resetProgress();

        setTimeout(() => {
            this.isTransitioning = false;
        }, 600);
    }

    go(index) {
        if (this.isTransitioning || index === this.current) return;
        this.isTransitioning = true;
        this.current = index;
        this.update();
        this.resetProgress();

        setTimeout(() => {
            this.isTransitioning = false;
        }, 600);
    }

    update() {
        this.wrapper.style.transform = `translateX(-${this.current * 100}%)`;

        const dots = this.container.querySelectorAll('.dot');
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === this.current);
            dot.setAttribute('aria-selected', i === this.current);
        });
    }

    pause() {
        if (this.autoplay) {
            clearInterval(this.autoplay);
            this.autoplay = null;
        }
    }

    startAutoplay() {
        this.pause();
        this.resetProgress();
        this.autoplay = setInterval(() => this.move(1), this.interval);
    }

    resetProgress() {
        if (this.progress) {
            this.progress.style.transition = 'none';
            this.progress.style.width = '0%';
            setTimeout(() => {
                this.progress.style.transition = `width ${this.interval}ms linear`;
                this.progress.style.width = '100%';
            }, 50);
        }
    }

    setupTouch() {
        let startX = 0;
        let endX = 0;

        this.container.addEventListener('touchstart', (e) => {
            startX = e.changedTouches[0].screenX;
            this.pause();
        }, { passive: true });

        this.container.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].screenX;
            const diff = startX - endX;

            if (Math.abs(diff) > 50) {
                if (diff > 0) this.move(1);
                else this.move(-1);
            }

            this.startAutoplay();
        }, { passive: true });
    }
}

// ================================
// FILTROS DE PRODUCTOS
// ================================
class Filtros {
    constructor() {
        this.buttons = document.querySelectorAll('.filtro-btn');
        this.productos = document.querySelectorAll('.producto');
        this.init();
    }

    init() {
        this.buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const filter = btn.dataset.filter;
                this.filter(filter);

                // Actualizar clase active
                this.buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
    }

    filter(categoria) {
        this.productos.forEach(p => {
            const matches = categoria === 'todos' || p.dataset.categoria === categoria;
            p.style.display = matches ? '' : 'none';

            if (matches) {
                p.style.animation = 'none';
                p.offsetHeight; // Trigger reflow
                p.style.animation = 'fadeIn 0.3s ease';
            }
        });
    }
}

// ================================
// MENÚ MÓVIL
// ================================
class MobileMenu {
    constructor() {
        this.toggle = document.querySelector('.menu-toggle');
        this.nav = document.getElementById('main-nav');
        this.init();
    }

    init() {
        if (this.toggle && this.nav) {
            this.toggle.addEventListener('click', () => this.toggleMenu());
        }
    }

    toggleMenu() {
        const isOpen = this.nav.classList.toggle('active');
        this.toggle.setAttribute('aria-expanded', isOpen);
    }
}

// ================================
// INICIALIZAR
// ================================
document.addEventListener('DOMContentLoaded', () => {
    // Slider
    const slider = document.querySelector('.slider');
    if (slider) {
        const wrapper = document.getElementById('slider-wrapper');
        new Slider(slider, wrapper);
    }

    // Filtros
    new Filtros();

    // Menú móvil
    new MobileMenu();

    // Auto-hide flash messages (5 segundos)
    setTimeout(() => {
        const flashes = document.querySelectorAll('.flash');
        flashes.forEach(flash => {
            flash.style.animation = 'slideOut 0.3s ease forwards';
        });
    }, 5000);
});

// animation fadeIn
const style = document.createElement('style');
style.textContent = `
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes slideOut {
    from { opacity: 1; transform: translateX(0); }
    to { opacity: 0; transform: translateX(100%); }
}
`;
document.head.appendChild(style);