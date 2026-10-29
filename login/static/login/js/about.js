/**
 * GuardianTree FP — About Us Page Interactive Scripts
 * Handles Team Accordion Expansion, Slider Carousel Controls, Dots, and Mobile Touch Swipe.
 * Responsive: displays one member at a time on mobile (<=768px) and 4 on desktop.
 */

document.addEventListener("DOMContentLoaded", function () {
  const cards = document.querySelectorAll(".team-member-card");
  const controls = document.getElementById("team-controls");
  const dotsContainer = document.getElementById("team-dots");
  const prevBtn = document.getElementById("team-prev-btn");
  const nextBtn = document.getElementById("team-next-btn");

  if (!cards || cards.length === 0) return;

  let currentIdx = 0;
  const totalCount = cards.length;
  let visibleCount = getVisibleCount();

  function getVisibleCount() {
    return window.innerWidth <= 768 ? 1 : 4;
  }

  function renderDots(visibleCount) {
    if (!dotsContainer) return;
    dotsContainer.innerHTML = "";
    if (totalCount > visibleCount) {
      const dotCount = totalCount - visibleCount + 1;
      for (let i = 0; i < dotCount; i++) {
        const dot = document.createElement("button");
        dot.className = "team-slider-dot";
        dot.setAttribute("type", "button");
        dot.setAttribute("aria-label", `Go to team members starting from ${i + 1}`);
        dot.addEventListener("click", function () {
          currentIdx = i;
          updateSlider();
        });
        dotsContainer.appendChild(dot);
      }
    }
  }

  function updateSlider() {
    visibleCount = getVisibleCount();
    const maxStart = Math.max(0, totalCount - visibleCount);
    currentIdx = Math.min(currentIdx, maxStart);

    // 1. Update the visibility of the cards
    cards.forEach((card, idx) => {
      if (totalCount > visibleCount) {
        if (idx >= currentIdx && idx < currentIdx + visibleCount) {
          card.classList.remove("team-member-hidden");
        } else {
          card.classList.add("team-member-hidden");
        }
      } else {
        card.classList.remove("team-member-hidden");
      }

      // Remove active states
      card.classList.remove("active-first");
      card.classList.remove("is-active");
    });

    // 2. Set the first visible card as active-first (expanded when accordion is not hovered or tapped)
    const firstVisibleCard = cards[currentIdx];
    if (firstVisibleCard) {
      firstVisibleCard.classList.add("active-first");
    }

    // 3. Show/hide controls and update states
    if (controls) {
      if (totalCount > visibleCount) {
        controls.style.display = "flex";
      } else {
        controls.style.display = "none";
      }
    }

    // 4. Update the dot active states
    if (dotsContainer && totalCount > visibleCount) {
      const dots = dotsContainer.querySelectorAll(".team-slider-dot");
      dots.forEach((dot, idx) => {
        dot.classList.toggle("active", idx === currentIdx);
      });
    }

  if (controls && dotsContainer && prevBtn && nextBtn) {
    // Show controls
    controls.style.display = "flex";

    function rebuildDots() {
      dotsContainer.innerHTML = "";
      const dotCount = Math.max(1, totalCount - getVisibleCount() + 1);
      for (let i = 0; i < dotCount; i++) {
        const dot = document.createElement("button");
        dot.className = "team-slider-dot";
        dot.setAttribute("aria-label", `Go to team members starting from ${i + 1}`);
        dot.addEventListener("click", function () {
          currentIdx = i;
          updateSlider();
        });
        dotsContainer.appendChild(dot);
      }
    }

    rebuildDots();

    // Prev and Next Button Listeners
    prevBtn.addEventListener("click", function () {
      if (currentIdx > 0) {
        currentIdx--;
        updateSlider();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      if (currentIdx < totalCount - getVisibleCount()) {
        currentIdx++;
        updateSlider();
      }
    });
  }

  // Interactive Card Click / Tap Expansion (Mobile and Desktop)
  cards.forEach((card) => {
    card.addEventListener("click", function () {
      if (this.classList.contains("team-member-hidden")) return;
      cards.forEach((c) => {
        c.classList.remove("active-first");
        c.classList.remove("is-active");
      });
      this.classList.add("is-active");
    });
  });

  // Mobile touch swipe support
  const accordion = document.querySelector(".team-members-accordion");
  if (accordion) {
    let touchStartX = 0;
    let touchEndX = 0;

    accordion.addEventListener("touchstart", function (e) {
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    accordion.addEventListener("touchend", function (e) {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipe();
    }, { passive: true });

    function handleSwipe() {
      const visibleCount = getVisibleCount();
      const maxIdx = Math.max(0, totalCount - visibleCount);
      const swipeThreshold = 40; // pixels
      if (touchStartX - touchEndX > swipeThreshold) {
        // Swiped left -> Next
        if (currentIdx < maxIdx) {
          currentIdx++;
          updateSlider();
        }
      } else if (touchEndX - touchStartX > swipeThreshold) {
        // Swiped right -> Prev
        if (currentIdx > 0) {
          currentIdx--;
          updateSlider();
        }
      }
    }

    // Card click / tap listener for mobile and PC expansion
    cards.forEach(card => {
      card.addEventListener("click", function () {
        cards.forEach(c => c.classList.remove("active-first"));
        card.classList.add("active-first");
      });
    });

    window.addEventListener("resize", function () {
      const nextVisibleCount = getVisibleCount();
      if (nextVisibleCount !== visibleCount) {
        visibleCount = nextVisibleCount;
        rebuildDots();
        updateSlider();
      }
    });
  }

  // Handle Window Resize to switch between 2 and 4 visible count
  let resizeTimer = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      const visibleCount = getVisibleCount();
      renderDots(visibleCount);
      updateSlider();
    }, 150);
  });

  // Initialize
  renderDots(getVisibleCount());
  updateSlider();
});

