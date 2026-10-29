/**
 * GuardianTree FP — Executive Homepage Scripts
 * Includes Wealth Simulator, FAQ Search & Pagination, Video Controls, and Scroll Animations.
 */

let currentSimType = 'sip';
let currentRate = 13.5;
let currentHorizon = 15;

function setSimType(type) {
  currentSimType = type;
  const btnSip = document.getElementById('btn-sip');
  const btnLump = document.getElementById('btn-lumpsum');
  if (btnSip) {
    btnSip.classList.toggle('active', type === 'sip');
    btnSip.setAttribute('aria-pressed', type === 'sip' ? 'true' : 'false');
  }
  if (btnLump) {
    btnLump.classList.toggle('active', type === 'lumpsum');
    btnLump.setAttribute('aria-pressed', type === 'lumpsum' ? 'true' : 'false');
  }

  const label = document.getElementById('sim-amount-label');
  const slider = document.getElementById('sim-amount');

  if (slider) {
    if (type === 'sip') {
      if (label) label.innerText = 'Monthly Investment';
      slider.min = 5000;
      slider.max = 500000;
      slider.step = 5000;
      slider.value = 50000;
      slider.setAttribute('aria-label', 'Monthly Investment Amount');
    } else {
      if (label) label.innerText = 'One-Time Lumpsum';
      slider.min = 100000;
      slider.max = 10000000;
      slider.step = 50000;
      slider.value = 1000000;
      slider.setAttribute('aria-label', 'One-Time Lumpsum Amount');
    }
  }
  
  if (typeof announceToScreenReader === 'function') {
    announceToScreenReader(`Investment mode updated to ${type === 'sip' ? 'Monthly SIP' : 'One-Time Lumpsum'}.`);
  }
  updateSimulator();
}

function selectStrategy(rate, el) {
  currentRate = rate;
  document.querySelectorAll('.strategy-option').forEach(opt => {
    opt.classList.remove('active');
    opt.setAttribute('aria-checked', 'false');
  });
  if (el) {
    el.classList.add('active');
    el.setAttribute('aria-checked', 'true');
    const stratName = el.querySelector('.strat-title')?.innerText || 'Growth Strategy';
    if (typeof announceToScreenReader === 'function') {
      announceToScreenReader(`Growth Strategy selected: ${stratName} at ${rate}% per annum.`);
    }
  }
  updateSimulator();
}

function setHorizon(years, el) {
  currentHorizon = years;
  document.querySelectorAll('.horizon-pill').forEach(btn => {
    btn.classList.remove('active');
    btn.setAttribute('aria-pressed', 'false');
  });
  if (el) {
    el.classList.add('active');
    el.setAttribute('aria-pressed', 'true');
  }
  const yearsVal = document.getElementById('sim-years-val');
  if (yearsVal) yearsVal.innerText = years + ' Years';
  if (typeof announceToScreenReader === 'function') {
    announceToScreenReader(`Time Horizon updated to ${years} Years.`);
  }
  updateSimulator();
}

function formatINR(val) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(val);
}

function updateSimulator() {
  const amountEl = document.getElementById('sim-amount');
  if (!amountEl) return;
  const amount = parseFloat(amountEl.value);
  const amountValEl = document.getElementById('sim-amount-val');
  if (amountValEl) {
    amountValEl.innerText = formatINR(amount) + (currentSimType === 'sip' ? ' / mo' : '');
  }

  amountEl.setAttribute('aria-valuenow', amount);
  amountEl.setAttribute('aria-valuetext', `${formatINR(amount)} ${currentSimType === 'sip' ? 'per month' : 'one-time'}`);

  let totalInvested = 0;
  let totalWealth = 0;
  const r = currentRate / 100;
  const n = currentHorizon;

  if (currentSimType === 'sip') {
    const monthlyRate = r / 12;
    const totalMonths = n * 12;
    totalInvested = amount * totalMonths;
    totalWealth = amount * ((Math.pow(1 + monthlyRate, totalMonths) - 1) / monthlyRate) * (1 + monthlyRate);
  } else {
    totalInvested = amount;
    totalWealth = amount * Math.pow(1 + r, n);
  }

  const yieldGain = Math.max(0, totalWealth - totalInvested);
  const pctInvested = Math.round((totalInvested / Math.max(1, totalWealth)) * 100);
  const pctGain = 100 - pctInvested;

  const totalWealthEl = document.getElementById('res-total-wealth');
  const investedEl = document.getElementById('res-invested');
  const returnsEl = document.getElementById('res-returns');
  const boostTagEl = document.getElementById('res-boost-tag');
  const pctInvestedEl = document.getElementById('pct-invested');
  const pctGainEl = document.getElementById('pct-gain');
  const barPrincipalFill = document.getElementById('bar-principal-fill');
  const barYieldFill = document.getElementById('bar-yield-fill');

  if (totalWealthEl) totalWealthEl.innerText = formatINR(totalWealth);
  if (investedEl) investedEl.innerText = formatINR(totalInvested);
  if (returnsEl) returnsEl.innerText = formatINR(yieldGain);
  if (boostTagEl) boostTagEl.innerText = '🔥 +' + formatINR(yieldGain) + ' Capital Compounded';

  if (pctInvestedEl) pctInvestedEl.innerText = pctInvested + '%';
  if (pctGainEl) pctGainEl.innerText = pctGain + '%';
  if (barPrincipalFill) barPrincipalFill.style.width = pctInvested + '%';
  if (barYieldFill) barYieldFill.style.width = pctGain + '%';
}

// FAQ Interactive Pagination, Search & Video Controller
let currentFaqPage = 1;
const faqsPerPage = 3;

function toggleFaq(cardEl) {
  const isOpen = cardEl.classList.contains('open');
  document.querySelectorAll('.faq-card').forEach(c => {
    c.classList.remove('open');
    c.setAttribute('aria-expanded', 'false');
  });
  if (!isOpen) {
    cardEl.classList.add('open');
    cardEl.setAttribute('aria-expanded', 'true');
    const qText = cardEl.querySelector('.faq-question-text')?.innerText || '';
    const aText = cardEl.querySelector('.faq-answer-text')?.innerText || '';
    if (typeof announceToScreenReader === 'function') {
      announceToScreenReader(`FAQ expanded: ${qText}`);
    }
    if (typeof speechEnabled !== 'undefined' && speechEnabled && typeof speakText === 'function') {
      speakText(`Question: ${qText}. Answer: ${aText}`);
    }
  } else {
    if (typeof announceToScreenReader === 'function') {
      announceToScreenReader('FAQ item collapsed.');
    }
  }
}

function getMatchingFaqCards() {
  const searchInput = document.getElementById('faq-search-input');
  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const clearBtn = document.getElementById('faq-search-clear');
  if (clearBtn) {
    clearBtn.style.display = query.length > 0 ? 'flex' : 'none';
  }

  const allCards = Array.from(document.querySelectorAll('#faq-accordion-list .faq-card'));
  if (!query) {
    return allCards;
  }

  return allCards.filter(card => {
    const qText = (card.getAttribute('data-question') || card.querySelector('.faq-question-text')?.innerText || '').toLowerCase();
    const aText = (card.getAttribute('data-answer') || card.querySelector('.faq-answer-text')?.innerText || '').toLowerCase();
    const catText = (card.getAttribute('data-category') || card.querySelector('.faq-badge-category')?.innerText || '').toLowerCase();
    return qText.includes(query) || aText.includes(query) || catText.includes(query);
  });
}

function renderFaqPage() {
  const accordionList = document.getElementById('faq-accordion-list');
  if (!accordionList) return;
  const allCards = Array.from(accordionList.querySelectorAll('.faq-card'));
  if (allCards.length === 0) return;

  const matchingCards = getMatchingFaqCards();
  const noResultsEl = document.getElementById('faq-no-results');
  const paginationWrapper = document.getElementById('faq-pagination-controls');

  if (matchingCards.length === 0) {
    allCards.forEach(card => card.style.display = 'none');
    if (noResultsEl) noResultsEl.style.display = 'block';
    if (paginationWrapper) paginationWrapper.style.display = 'none';
    return;
  }

  if (noResultsEl) noResultsEl.style.display = 'none';
  if (paginationWrapper) paginationWrapper.style.display = 'flex';

  const totalPages = Math.ceil(matchingCards.length / faqsPerPage);
  if (currentFaqPage > totalPages) currentFaqPage = totalPages;
  if (currentFaqPage < 1) currentFaqPage = 1;

  // Hide all cards first
  allCards.forEach(card => card.style.display = 'none');

  // Show only cards for the current page
  const startIndex = (currentFaqPage - 1) * faqsPerPage;
  const endIndex = startIndex + faqsPerPage;
  const currentBatch = matchingCards.slice(startIndex, endIndex);

  currentBatch.forEach((card, idx) => {
    card.style.display = 'block';
    card.style.opacity = '0';
    card.style.transform = 'translateY(10px)';
    setTimeout(() => {
      card.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, idx * 60);
  });

  // Update Pagination Buttons
  const prevBtn = document.getElementById('faq-prev-btn');
  const nextBtn = document.getElementById('faq-next-btn');
  if (prevBtn) prevBtn.disabled = (currentFaqPage === 1);
  if (nextBtn) nextBtn.disabled = (currentFaqPage === totalPages || totalPages === 0);

  // Update Page Number Indicators
  const indicatorsContainer = document.getElementById('faq-page-indicators');
  if (indicatorsContainer) {
    indicatorsContainer.innerHTML = '';
    for (let i = 1; i <= totalPages; i++) {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = `faq-page-dot ${i === currentFaqPage ? 'active' : ''}`;
      dot.innerText = i;
      dot.onclick = () => {
        currentFaqPage = i;
        renderFaqPage();
      };
      indicatorsContainer.appendChild(dot);
    }
  }
}

function changeFaqPage(direction) {
  currentFaqPage += direction;
  renderFaqPage();
}

function handleFaqSearch() {
  currentFaqPage = 1;
  renderFaqPage();
}

function clearFaqSearch() {
  const input = document.getElementById('faq-search-input');
  if (input) input.value = '';
  currentFaqPage = 1;
  renderFaqPage();
}

function toggleFaqVideoPlay() {
  const video = document.getElementById('faq-main-video');
  const playIcon = document.getElementById('faq-play-icon');
  const statusText = document.getElementById('faq-video-status');
  if (!video) return;

  if (video.paused) {
    video.play().catch(() => { });
    if (playIcon) {
      playIcon.innerHTML = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
    }
    if (statusText) statusText.innerText = '▶ Playing Video';
  } else {
    video.pause();
    if (playIcon) {
      playIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
    }
    if (statusText) statusText.innerText = '⏸ Paused Video';
  }
}

function toggleFaqVideoMute(event) {
  if (event) event.stopPropagation();
  const video = document.getElementById('faq-main-video');
  const muteIcon = document.getElementById('faq-mute-icon');
  const voiceLabel = document.getElementById('faq-voice-label');
  if (!video) return;

  video.muted = !video.muted;

  if (video.muted) {
    if (muteIcon) {
      muteIcon.innerHTML = '<path d="M11 5L6 9H2V15H6L11 19V5Z"></path><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line>';
    }
    if (voiceLabel) voiceLabel.innerText = 'Muted';
  } else {
    if (muteIcon) {
      muteIcon.innerHTML = '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>';
    }
    if (voiceLabel) voiceLabel.innerText = 'Sound On';
  }
}

document.addEventListener("DOMContentLoaded", function () {
  updateSimulator();
  renderFaqPage();

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.remove('fade-up-enter');
        entry.target.classList.add('fade-up-enter-active');

        setTimeout(() => {
          entry.target.classList.remove('fade-up-enter-active');
        }, 600);

        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -50px 0px" });

  const animElements = document.querySelectorAll('.compliance-section-wrapper .section-header, .compliance-card, .compliance-trust-bar, .wealth-simulator-wrapper .section-header, .sim-controls-card, .sim-results-card, .faq-section-wrapper .section-header, .faq-card');
  animElements.forEach((el, index) => {
    el.classList.add('fade-up-enter');
    if (el.classList.contains('compliance-card') || el.classList.contains('sim-controls-card') || el.classList.contains('sim-results-card') || el.classList.contains('faq-card')) {
      el.style.transitionDelay = `${(index % 4) * 0.12}s`;
      setTimeout(() => el.style.transitionDelay = '0s', 600 + ((index % 4) * 120));
    }
    observer.observe(el);
  });
});
