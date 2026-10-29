/**
 * GuardianTree FP — Client Testimonials Interactive Controller
 * Handles modal popups, review details, submission form modal, keyword search and leader grid filters.
 */

var activeCategory = 'all';

function openReviewModal(name, role, location, quote, rating, avatar, highlight) {
  const mName = document.getElementById('mName');
  const mRole = document.getElementById('mRole');
  const mLocation = document.getElementById('mLocation');
  const mQuote = document.getElementById('mQuote');
  const mStars = document.getElementById('mStars');
  const mHighlight = document.getElementById('mHighlight');

  if (mName) mName.textContent = name;
  if (mRole) mRole.textContent = role;
  if (mLocation) mLocation.textContent = '📍 ' + location;
  if (mQuote) mQuote.textContent = '"' + quote + '"';
  if (mStars) mStars.textContent = rating;
  if (mHighlight) mHighlight.textContent = highlight || 'Verified Fiduciary Account';

  const avatarWrapper = document.getElementById('mAvatarWrapper');
  if (avatarWrapper) {
    if (avatar && avatar !== '') {
      avatarWrapper.innerHTML = `<img id="mAvatar" src="${avatar}" alt="${name}" style="width: 64px; height: 64px; border-radius: 50%; object-fit: cover; border: 2px solid var(--color-gold); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);">`;
    } else {
      const firstLetter = (name && name.length > 0) ? name.charAt(0).toUpperCase() : 'U';
      avatarWrapper.innerHTML = `
        <div style="width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, #FFD700 0%, #F59E0B 100%); color: #0A0D14; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1.6rem; border: 2px solid var(--color-gold); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);">
          ${firstLetter}
        </div>
      `;
    }
  }

  const modal = document.getElementById('detailModal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeReviewModal(e) {
  const detailModal = document.getElementById('detailModal');
  if (e && e.target !== detailModal && !e.target.classList.contains('modal-close-btn')) {
    return;
  }
  if (detailModal) {
    detailModal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

function openWriteModal() {
  const modal = document.getElementById('writeModal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeWriteModal(e) {
  const writeModal = document.getElementById('writeModal');
  if (e && e.target !== writeModal && !e.target.classList.contains('modal-close-btn')) {
    return;
  }
  if (writeModal) {
    writeModal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// Close modals on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeReviewModal();
    closeWriteModal();
  }
});

function filterCategory(btn) {
  const btns = document.querySelectorAll('.dock-filter-btn');
  btns.forEach(b => b.classList.remove('active'));
  if (btn) {
    btn.classList.add('active');
    activeCategory = btn.getAttribute('data-category');
  }
  applyCombinedFilters();
}

function filterLeadersGrid() {
  applyCombinedFilters();
}

function applyCombinedFilters() {
  const searchInput = document.getElementById('testimonialSearchInput') || document.getElementById('dockSearchInput');
  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const clearBtn = document.getElementById('testimonialSearchClear');
  if (clearBtn) {
    clearBtn.style.display = query.length > 0 ? 'block' : 'none';
  }

  const portraitCards = document.querySelectorAll('.leader-portrait-card');
  let matchCount = 0;

  portraitCards.forEach(card => {
    const cardName = (card.getAttribute('data-name') || '').toLowerCase();
    const cardRole = (card.getAttribute('data-role') || '').toLowerCase();
    const cardLocation = (card.getAttribute('data-location') || '').toLowerCase();
    const cardQuote = (card.getAttribute('data-quote') || '').toLowerCase();
    const cardCategory = (card.getAttribute('data-category') || '').toLowerCase();
    const cardOnclick = (card.getAttribute('onclick') || '').toLowerCase();

    const fullContent = `${cardName} ${cardRole} ${cardLocation} ${cardQuote} ${cardCategory} ${cardOnclick}`;

    // Category Match
    let categoryMatch = false;
    if (activeCategory === 'all') {
      categoryMatch = true;
    } else if (activeCategory === 'entrepreneur' && fullContent.includes('entrepreneur')) {
      categoryMatch = true;
    } else if (activeCategory === 'portfolio_manager' && (fullContent.includes('portfolio manager') || fullContent.includes('wealth'))) {
      categoryMatch = true;
    } else if (activeCategory === 'saver' && fullContent.includes('saver')) {
      categoryMatch = true;
    } else if (activeCategory === 'institutional' && (fullContent.includes('trustee') || fullContent.includes('executive') || fullContent.includes('institutional') || fullContent.includes('director'))) {
      categoryMatch = true;
    }

    // Keyword Match
    const keywordMatch = !query || fullContent.includes(query);

    if (categoryMatch && keywordMatch) {
      matchCount++;
      card.style.opacity = '1';
      card.style.pointerEvents = 'auto';
      if (query.length > 0) {
        card.style.transform = 'scale(1.06) translateY(-4px)';
        card.style.border = '2px solid var(--color-gold, #D4AF37)';
        card.style.boxShadow = '0 12px 30px rgba(212, 175, 55, 0.4)';
      } else {
        card.style.transform = '';
        card.style.border = '';
        card.style.boxShadow = '';
      }
    } else {
      card.style.opacity = '0.12';
      card.style.transform = 'scale(0.85)';
      card.style.pointerEvents = 'none';
      card.style.border = '';
      card.style.boxShadow = '';
    }
  });

  const feedback = document.getElementById('testimonialSearchFeedback');
  if (feedback) {
    if (query.length > 0) {
      feedback.style.display = 'block';
      if (matchCount > 0) {
        feedback.textContent = `Found ${matchCount} client review${matchCount > 1 ? 's' : ''} matching "${query}". Click any portrait to read details.`;
        feedback.style.color = 'var(--color-gold, #D4AF37)';
      } else {
        feedback.textContent = `No client reviews found matching "${query}". Displaying all portraits dimmed.`;
        feedback.style.color = '#EF4444';
      }
    } else {
      feedback.style.display = 'none';
      feedback.textContent = '';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('testimonialSearchInput');
  const searchBtn = document.getElementById('testimonialSearchBtn');
  const clearBtn = document.getElementById('testimonialSearchClear');

  if (searchInput) {
    searchInput.addEventListener('input', applyCombinedFilters);
    searchInput.addEventListener('keyup', (e) => {
      if (e.key === 'Enter') {
        const firstMatch = document.querySelector('.leader-portrait-card[style*="opacity: 1"]');
        if (firstMatch) firstMatch.click();
      }
      applyCombinedFilters();
    });
    searchInput.addEventListener('search', applyCombinedFilters);
  }

  if (searchBtn) {
    searchBtn.addEventListener('click', applyCombinedFilters);
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      applyCombinedFilters();
      if (searchInput) searchInput.focus();
    });
  }
});
