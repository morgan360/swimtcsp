// Hero Text Carousel
class HeroCarousel {
    constructor() {
        this.slides = [
            {
                title: 'Swimming is for <span class="text-red-400">life!</span>',
                subtitle: 'Dive in with our community - whether you\'re a beginner or expert, we\'re here to support your swimming journey.'
            },
            {
                title: 'All-new <span class="text-red-400">swimling dashboard!</span>',
                subtitle: 'Register as a <span class="text-red-400">Guardian</span> and manage all your swimmers in one place with the new swimling dashboard.'
            },
            {
                title: 'swimling <span class="text-red-400">/ˈswɪm·lɪŋ/</span> <span class="text-white/80 text-base align-middle">noun</span>',
                subtitle: '<span class="block">1. A student in a <strong>swimming class</strong>; a young swimmer in training.</span><span class="block">2. A swimmer managed by a <strong>Guardian</strong> via the <em>Swimling Dashboard</em>.</span>'
            },
            {
                title: 'Learn to swim with <span class="text-red-400">confidence!</span>',
                subtitle: 'Our certified instructors provide expert guidance for all ages and abilities. From first splash to competitive strokes.'
            },
            {
                title: 'More than just <span class="text-red-400">swimming!</span>',
                subtitle: 'Join our vibrant community for fitness, fun, and friendship. Public swims, lessons, events, and more await you.'
            }
        ];
        
        this.currentSlide = 0;
        this.autoSlideInterval = null;
        this.isTransitioning = false;
        
        this.init();
    }
    
    init() {
        this.createCarouselHTML();
        this.bindEvents();
        this.startAutoSlide();
        this.showSlide(0);
    }
    
    createCarouselHTML() {
        const heroContent = document.querySelector('.hero-content');
        if (!heroContent) return;
        
        // Create carousel container
        const carouselContainer = document.createElement('div');
        carouselContainer.className = 'carousel-container relative w-full max-w-4xl mx-auto';
        
        // Create slides container
        const slidesContainer = document.createElement('div');
        slidesContainer.className = 'slides-container relative w-full min-h-[200px] overflow-hidden';
        slidesContainer.id = 'hero-slides';
        
        // Create slides
        this.slides.forEach((slide, index) => {
            const slideElement = document.createElement('div');
            slideElement.className = `slide absolute inset-0 flex flex-col justify-center items-center text-center transition-all duration-700 ease-in-out ${index === 0 ? 'opacity-100 transform translate-x-0' : 'opacity-0 transform translate-x-8'}`;
            slideElement.setAttribute('data-slide', index);
            
            slideElement.innerHTML = `
                <h2 class="text-4xl font-bold leading-tight mb-4 drop-shadow-lg text-white transform transition-transform duration-700 ease-out">${slide.title}</h2>
                <p class="text-lg sm:text-xl md:text-2xl font-medium text-white/90 mb-8 max-w-2xl mx-auto drop-shadow-md transform transition-transform duration-700 ease-out delay-100">${slide.subtitle}</p>
            `;
            
            slidesContainer.appendChild(slideElement);
        });
        
        // Create indicators
        const indicatorsContainer = document.createElement('div');
        indicatorsContainer.className = 'indicators-container flex justify-center space-x-2 mt-8';
        indicatorsContainer.id = 'hero-indicators';
        
        this.slides.forEach((_, index) => {
            const indicator = document.createElement('button');
            indicator.className = `indicator w-3 h-3 rounded-full transition-all duration-300 ${index === 0 ? 'bg-white' : 'bg-white/40 hover:bg-white/60'}`;
            indicator.setAttribute('data-slide', index);
            indicator.setAttribute('aria-label', `Go to slide ${index + 1}`);
            
            indicatorsContainer.appendChild(indicator);
        });
        
        // Assemble carousel
        carouselContainer.appendChild(slidesContainer);
        carouselContainer.appendChild(indicatorsContainer);
        
        // Replace existing content
        heroContent.innerHTML = '';
        heroContent.appendChild(carouselContainer);
    }
    
    bindEvents() {
        // Indicator click events
        const indicators = document.querySelectorAll('#hero-indicators .indicator');
        indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => {
                this.goToSlide(index);
            });
        });
        
        // Pause on hover
        const carouselContainer = document.querySelector('.carousel-container');
        if (carouselContainer) {
            carouselContainer.addEventListener('mouseenter', () => {
                this.pauseAutoSlide();
            });
            
            carouselContainer.addEventListener('mouseleave', () => {
                this.startAutoSlide();
            });
        }
    }
    
    showSlide(index) {
        if (this.isTransitioning || index === this.currentSlide) return;
        
        this.isTransitioning = true;
        
        const slides = document.querySelectorAll('#hero-slides .slide');
        const indicators = document.querySelectorAll('#hero-indicators .indicator');
        const currentSlideElement = slides[this.currentSlide];
        const nextSlideElement = slides[index];
        
        // Determine slide direction
        const isForward = index > this.currentSlide || (this.currentSlide === this.slides.length - 1 && index === 0);
        
        // Phase 1: Hide current slide
        if (currentSlideElement) {
            currentSlideElement.classList.remove('opacity-100', 'translate-x-0');
            currentSlideElement.classList.add('opacity-0', isForward ? '-translate-x-8' : 'translate-x-8');
        }
        
        // Phase 2: Prepare next slide (off-screen)
        if (nextSlideElement) {
            nextSlideElement.classList.remove('opacity-0', 'translate-x-8', '-translate-x-8');
            nextSlideElement.classList.add('opacity-0', isForward ? 'translate-x-8' : '-translate-x-8');
        }
        
        // Phase 3: Show next slide after a brief delay
        setTimeout(() => {
            if (nextSlideElement) {
                nextSlideElement.classList.remove('opacity-0', 'translate-x-8', '-translate-x-8');
                nextSlideElement.classList.add('opacity-100', 'translate-x-0');
            }
            
            // Update indicators
            indicators.forEach((indicator, i) => {
                if (i === index) {
                    indicator.classList.remove('bg-white/40');
                    indicator.classList.add('bg-white');
                } else {
                    indicator.classList.remove('bg-white');
                    indicator.classList.add('bg-white/40');
                }
            });
            
            this.currentSlide = index;
            
            // Reset transition flag after animation completes
            setTimeout(() => {
                this.isTransitioning = false;
            }, 700); // Match the CSS transition duration
            
        }, 100); // Small delay to ensure smooth transition
    }
    
    goToSlide(index) {
        if (index === this.currentSlide || this.isTransitioning) return;
        this.showSlide(index);
    }
    
    nextSlide() {
        const nextIndex = (this.currentSlide + 1) % this.slides.length;
        this.showSlide(nextIndex);
    }
    
    startAutoSlide() {
        this.pauseAutoSlide(); // Clear any existing interval
        this.autoSlideInterval = setInterval(() => {
            this.nextSlide();
        }, 5000); // Change slide every 5 seconds
    }
    
    pauseAutoSlide() {
        if (this.autoSlideInterval) {
            clearInterval(this.autoSlideInterval);
            this.autoSlideInterval = null;
        }
    }
    
    destroy() {
        this.pauseAutoSlide();
        // Clean up event listeners if needed
    }
}

// Initialize carousel when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on a page with hero content
    const heroContent = document.querySelector('.hero-content');
    if (heroContent) {
        window.heroCarousel = new HeroCarousel();
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.heroCarousel) {
        window.heroCarousel.destroy();
    }
});
