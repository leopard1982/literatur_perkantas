(function($) {

    "use strict";

    var searchPopup = function() {
      // open search box
      $('#header-nav').on('click', '.search-button', function(e) {
        $('.search-popup').toggleClass('is-visible');
      });

      $('#header-nav').on('click', '.btn-close-search', function(e) {
        $('.search-popup').toggleClass('is-visible');
      });
      
      $(".search-popup-trigger").on("click", function(b) {
          b.preventDefault();
          $(".search-popup").addClass("is-visible"),
          setTimeout(function() {
              $(".search-popup").find("#search-popup").focus()
          }, 350)
      }),
      $(".search-popup").on("click", function(b) {
          ($(b.target).is(".search-popup-close") || $(b.target).is(".search-popup-close svg") || $(b.target).is(".search-popup-close path") || $(b.target).is(".search-popup")) && (b.preventDefault(),
          $(this).removeClass("is-visible"))
      }),
      $(document).keyup(function(b) {
          "27" === b.which && $(".search-popup").removeClass("is-visible")
      })
    }

    var countdownTimer = function() {
      function getTimeRemaining(endtime) {
        const total = Date.parse(endtime) - Date.parse(new Date());
        const seconds = Math.floor((total / 1000) % 60);
        const minutes = Math.floor((total / 1000 / 60) % 60);
        const hours = Math.floor((total / (1000 * 60 * 60)) % 24);
        const days = Math.floor(total / (1000 * 60 * 60 * 24));
        return {
          total,
          days,
          hours,
          minutes,
          seconds
        };
      }
  
      function initializeClock(id, endtime) {
        const clock = document.getElementById(id);
        const daysSpan = clock.querySelector('.days');
        const hoursSpan = clock.querySelector('.hours');
        const minutesSpan = clock.querySelector('.minutes');
        const secondsSpan = clock.querySelector('.seconds');
  
        function updateClock() {
          const t = getTimeRemaining(endtime);
          daysSpan.innerHTML = t.days;
          hoursSpan.innerHTML = ('0' + t.hours).slice(-2);
          minutesSpan.innerHTML = ('0' + t.minutes).slice(-2);
          secondsSpan.innerHTML = ('0' + t.seconds).slice(-2);
          if (t.total <= 0) {
            clearInterval(timeinterval);
          }
        }
        updateClock();
        const timeinterval = setInterval(updateClock, 1000);
      }
  
      $('#countdown-clock').each(function(){
        const deadline = new Date(Date.parse(new Date()) + 28 * 24 * 60 * 60 * 1000);
        initializeClock('countdown-clock', deadline);
      });
    }

    var initProductQty = function(){

      $('.product-qty').each(function(){

        var $el_product = $(this);
        var quantity = 0;

        $el_product.find('.quantity-right-plus').click(function(e){
            e.preventDefault();
            var quantity = parseInt($el_product.find('#quantity').val());
            $el_product.find('#quantity').val(quantity + 1);
        });

        $el_product.find('.quantity-left-minus').click(function(e){
            e.preventDefault();
            var quantity = parseInt($el_product.find('#quantity').val());
            if(quantity>0){
              $el_product.find('#quantity').val(quantity - 1);
            }
        });

      });

    }

    $(document).ready(function() {

      searchPopup();
      initProductQty();
      countdownTimer();

      /* Video */
      var $videoSrc;  
        $('.play-btn').click(function() {
          $videoSrc = $(this).data( "src" );
        });

      if ($('#myModal').length && $('#video').length) {
        $('#myModal').on('shown.bs.modal', function (e) {
          if ($videoSrc) {
            $("#video").attr('src', $videoSrc + "?autoplay=1&amp;modestbranding=1&amp;showinfo=0");
          }
        })

        $('#myModal').on('hide.bs.modal', function (e) {
          $("#video").attr('src', $videoSrc || "");
        })
      }

      var mainSwiper = new Swiper(".main-swiper", {
        speed: 500,
        navigation: {
          nextEl: ".main-slider-button-next",
          prevEl: ".main-slider-button-prev",
        },
      });

      function getLoopThreshold(swiperOptions) {
        var maxSlidesPerView = Number(swiperOptions.slidesPerView) || 1;
        var maxSlidesPerGroup = Number(swiperOptions.slidesPerGroup) || 1;
        var breakpoints = swiperOptions.breakpoints || {};

        Object.keys(breakpoints).forEach(function(key) {
          var breakpoint = breakpoints[key] || {};
          var breakpointSlidesPerView = Number(breakpoint.slidesPerView);
          var breakpointSlidesPerGroup = Number(breakpoint.slidesPerGroup);

          if (!Number.isNaN(breakpointSlidesPerView)) {
            maxSlidesPerView = Math.max(maxSlidesPerView, breakpointSlidesPerView);
          }

          if (!Number.isNaN(breakpointSlidesPerGroup)) {
            maxSlidesPerGroup = Math.max(maxSlidesPerGroup, breakpointSlidesPerGroup);
          }
        });

        return Math.ceil(maxSlidesPerView) + maxSlidesPerGroup - 1;
      }

      function shouldEnableLoop(slideCount, swiperOptions) {
        if (slideCount <= 1) {
          return false;
        }

        return slideCount > getLoopThreshold(swiperOptions);
      }

      function createProductSwiper(selector, prevSelector, nextSelector) {
        var element = document.querySelector(selector);
        if (!element) {
          return null;
        }

        var slideCount = element.querySelector(".swiper-wrapper")
          ? element.querySelector(".swiper-wrapper").children.length
          : 0;

        var swiperOptions = {
          spaceBetween: 20,
          watchOverflow: true,
          navigation: {
            nextEl: nextSelector,
            prevEl: prevSelector,
          },
          breakpoints: {
            0: {
              slidesPerView: 1,
            },
            660: {
              slidesPerView: 3,
            },
            980: {
              slidesPerView: 4,
            },
            1500: {
              slidesPerView: 5,
            }
          },
        };

        swiperOptions.loop = shouldEnableLoop(slideCount, swiperOptions);

        return new Swiper(element, swiperOptions);
      }

      var bestSellerSwiper = createProductSwiper(
        ".best-seller-swiper",
        ".best-seller-slider-button-prev",
        ".best-seller-slider-button-next"
      );
      var freeBooksSwiper = createProductSwiper(
        ".free-books-swiper",
        ".free-books-slider-button-prev",
        ".free-books-slider-button-next"
      );

      var promoSpotlightSwiper = null;
      var instagramSwiper = null;
      var collectionShelfSwiper = null;
      var newBooksShelfSwiper = null;
      var promoShelfSwiper = null;
      var bestSellerManualNavBound = false;

      function syncManualNavState(swiperInstance, prevButton, nextButton) {
        if (!prevButton || !nextButton) {
          return;
        }

        if (!swiperInstance || swiperInstance.destroyed) {
          prevButton.classList.add("is-disabled");
          nextButton.classList.add("is-disabled");
          return;
        }

        if (swiperInstance.params.loop) {
          prevButton.classList.remove("is-disabled");
          nextButton.classList.remove("is-disabled");
          return;
        }

        prevButton.classList.toggle("is-disabled", swiperInstance.isBeginning);
        nextButton.classList.toggle("is-disabled", swiperInstance.isEnd);
      }

      function bindManualNav(swiperInstance, prevSelector, nextSelector) {
        var prevButton = document.querySelector(prevSelector);
        var nextButton = document.querySelector(nextSelector);

        syncManualNavState(swiperInstance, prevButton, nextButton);

        if (swiperInstance && !swiperInstance.destroyed) {
          var syncState = function() {
            syncManualNavState(swiperInstance, prevButton, nextButton);
          };

          swiperInstance.on("init", syncState);
          swiperInstance.on("slideChange", syncState);
          swiperInstance.on("update", syncState);
          swiperInstance.on("resize", syncState);
        }

        if (prevButton) {
          prevButton.onclick = function(event) {
            event.preventDefault();
            event.stopPropagation();
            if (swiperInstance && !swiperInstance.destroyed) {
              swiperInstance.update();
              swiperInstance.slidePrev(360);
            }
          };
        }

        if (nextButton) {
          nextButton.onclick = function(event) {
            event.preventDefault();
            event.stopPropagation();
            if (swiperInstance && !swiperInstance.destroyed) {
              swiperInstance.update();
              swiperInstance.slideNext(360);
            }
          };
        }
      }

      function bindBestSellerMobileNav() {
        if (bestSellerManualNavBound || !bestSellerSwiper) {
          return;
        }

        bindManualNav(bestSellerSwiper, ".best-seller-button-prev", ".best-seller-button-next");
        bestSellerManualNavBound = true;
      }

      function getRealSlideCount(swiperElement) {
        var wrapper = swiperElement ? swiperElement.querySelector(".swiper-wrapper") : null;
        if (!wrapper) {
          return 0;
        }
        return wrapper.children.length;
      }

      function initPromoSpotlightSwiper() {
        if (promoSpotlightSwiper && !promoSpotlightSwiper.destroyed) {
          promoSpotlightSwiper.destroy(true, true);
          promoSpotlightSwiper = null;
        }

        var promoSpotlightElement = document.querySelector(".promo-spotlight-swiper");
        if (!promoSpotlightElement) {
          return;
        }

        var promoSpotlightSlideCount = getRealSlideCount(promoSpotlightElement);
        var promoSpotlightShell = promoSpotlightElement.closest(".promo-spotlight-shell");
        var promoSpotlightPrevButton = promoSpotlightShell ? promoSpotlightShell.querySelector(".promo-spotlight-button-prev") : null;
        var promoSpotlightNextButton = promoSpotlightShell ? promoSpotlightShell.querySelector(".promo-spotlight-button-next") : null;

        var promoSpotlightOptions = {
          slidesPerView: 1,
          spaceBetween: 18,
          autoHeight: true,
          speed: 1200,
          allowTouchMove: true,
          observer: true,
          observeParents: true,
          watchOverflow: true,
          navigation: {
            prevEl: promoSpotlightPrevButton,
            nextEl: promoSpotlightNextButton,
          },
          autoplay: promoSpotlightSlideCount > 1 ? {
            delay: 5200,
            disableOnInteraction: false,
            pauseOnMouseEnter: false,
          } : false,
        };

        promoSpotlightOptions.loop = shouldEnableLoop(promoSpotlightSlideCount, promoSpotlightOptions);

        promoSpotlightSwiper = new Swiper(promoSpotlightElement, promoSpotlightOptions);

        if (promoSpotlightPrevButton) {
          promoSpotlightPrevButton.onclick = function(event) {
            event.preventDefault();
            promoSpotlightSwiper.slidePrev(420);
          };
        }

        if (promoSpotlightNextButton) {
          promoSpotlightNextButton.onclick = function(event) {
            event.preventDefault();
            promoSpotlightSwiper.slideNext(420);
          };
        }
      }

      function initNewBooksShelfSwiper() {
        if (newBooksShelfSwiper && !newBooksShelfSwiper.destroyed) {
          newBooksShelfSwiper.destroy(true, true);
          newBooksShelfSwiper = null;
        }

        if (window.innerWidth > 991.98) {
          return;
        }

        var newBooksElement = document.querySelector(".new-books-shelf-swiper");
        if (!newBooksElement) {
          return;
        }

        var newBooksSlideCount = getRealSlideCount(newBooksElement);

        var newBooksOptions = {
          slidesPerView: 1,
          spaceBetween: 18,
          grabCursor: true,
          autoHeight: true,
          centeredSlides: true,
          observer: true,
          observeParents: true,
          speed: 440,
          watchSlidesProgress: true,
        };

        newBooksOptions.loop = shouldEnableLoop(newBooksSlideCount, newBooksOptions);

        newBooksShelfSwiper = new Swiper(newBooksElement, newBooksOptions);

        bindManualNav(newBooksShelfSwiper, ".new-books-button-prev", ".new-books-button-next");
      }

      function initPromoShelfSwiper() {
        if (promoShelfSwiper && !promoShelfSwiper.destroyed) {
          promoShelfSwiper.destroy(true, true);
          promoShelfSwiper = null;
        }

        if (window.innerWidth > 991.98) {
          return;
        }

        var promoElement = document.querySelector(".promo-shelf-swiper");
        if (!promoElement) {
          return;
        }

        var promoSlideCount = getRealSlideCount(promoElement);

        var promoShelfOptions = {
          slidesPerView: 1,
          spaceBetween: 18,
          grabCursor: true,
          autoHeight: true,
          centeredSlides: true,
          observer: true,
          observeParents: true,
          speed: 440,
          watchSlidesProgress: true,
        };

        promoShelfOptions.loop = shouldEnableLoop(promoSlideCount, promoShelfOptions);

        promoShelfSwiper = new Swiper(promoElement, promoShelfOptions);

        bindManualNav(promoShelfSwiper, ".promo-button-prev", ".promo-button-next");
      }

      function initCollectionShelfSwiper() {
        if (collectionShelfSwiper && !collectionShelfSwiper.destroyed) {
          collectionShelfSwiper.destroy(true, true);
          collectionShelfSwiper = null;
        }

        if (window.innerWidth > 991.98) {
          return;
        }

        var collectionElement = document.querySelector(".collection-shelf-swiper");
        if (!collectionElement) {
          return;
        }

        var collectionSlideCount = getRealSlideCount(collectionElement);

        var collectionOptions = {
          slidesPerView: 1,
          spaceBetween: 18,
          grabCursor: true,
          autoHeight: true,
          centeredSlides: true,
          observer: true,
          observeParents: true,
          speed: 440,
          watchSlidesProgress: true,
        };

        collectionOptions.loop = shouldEnableLoop(collectionSlideCount, collectionOptions);

        collectionShelfSwiper = new Swiper(collectionElement, collectionOptions);

        bindManualNav(collectionShelfSwiper, ".collection-button-prev", ".collection-button-next");
      }

      function initInstagramSwiper() {
        if (instagramSwiper && !instagramSwiper.destroyed) {
          instagramSwiper.destroy(true, true);
          instagramSwiper = null;
        }

        if (window.innerWidth > 991.98) {
          return;
        }

        var instagramElement = document.querySelector(".insta-swiper");
        if (!instagramElement) {
          return;
        }

        var instagramSlideCount = getRealSlideCount(instagramElement);
        var instagramSection = instagramElement.closest(".instagram-section");
        var instagramPrevButton = instagramSection ? instagramSection.querySelector(".instagram-button-prev") : null;
        var instagramNextButton = instagramSection ? instagramSection.querySelector(".instagram-button-next") : null;

        var instagramOptions = {
          slidesPerView: 1.2,
          spaceBetween: 14,
          grabCursor: true,
          observer: true,
          observeParents: true,
          watchOverflow: true,
          speed: 420,
          navigation: {
            prevEl: instagramPrevButton,
            nextEl: instagramNextButton,
          },
          breakpoints: {
            480: {
              slidesPerView: 2.2,
            },
            640: {
              slidesPerView: 3.2,
            },
          },
        };

        instagramOptions.loop = shouldEnableLoop(instagramSlideCount, instagramOptions);

        instagramSwiper = new Swiper(instagramElement, instagramOptions);

        bindManualNav(instagramSwiper, ".instagram-button-prev", ".instagram-button-next");
      }

      initNewBooksShelfSwiper();
      window.addEventListener("resize", initNewBooksShelfSwiper);

      initPromoShelfSwiper();
      window.addEventListener("resize", initPromoShelfSwiper);

      initPromoSpotlightSwiper();
      window.addEventListener("resize", initPromoSpotlightSwiper);

      initCollectionShelfSwiper();
      window.addEventListener("resize", initCollectionShelfSwiper);

      initInstagramSwiper();
      window.addEventListener("resize", initInstagramSwiper);

      bindBestSellerMobileNav();

      var testimonialElement = document.querySelector(".testimonial-swiper");
      if (testimonialElement) {
        var testimonialSlideCount = getRealSlideCount(testimonialElement);
        var testimonialOptions = {
          slidesPerView: 1,
          spaceBetween: 20,
          autoHeight: true,
          speed: 440,
          navigation: {
            nextEl: ".testimonial-button-next",
            prevEl: ".testimonial-button-prev",
          },
        };

        testimonialOptions.loop = shouldEnableLoop(testimonialSlideCount, testimonialOptions);

        var testimonialSwiper = new Swiper(testimonialElement, testimonialOptions);

        bindManualNav(testimonialSwiper, ".testimonial-button-prev", ".testimonial-button-next");
      }

      var thumbSliderElement = document.querySelector(".thumb-swiper");
      var largeSliderElement = document.querySelector(".large-swiper");
      if (thumbSliderElement && largeSliderElement) {
        var thumb_slider = new Swiper(thumbSliderElement, {
          slidesPerView: 1,
        });
        var large_slider = new Swiper(largeSliderElement, {
          spaceBetween: 10,
          effect: 'fade',
          thumbs: {
            swiper: thumb_slider,
          },
        });
      }

    }); // End of a document ready

    window.addEventListener("load", function () {
      const preloader = document.getElementById("preloader");
      if (preloader) {
        preloader.classList.add("hide-preloader");
      }
    });

})(jQuery);
