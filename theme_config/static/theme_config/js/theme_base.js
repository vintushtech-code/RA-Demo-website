/**
 * GuardianTree FP — Master Base Theme Engine
 * Handles toast notifications and dynamic UI components.
 */

// Toast Notification Management
document.addEventListener('DOMContentLoaded', function () {
  const toasts = document.querySelectorAll('.toast-message-item');
  toasts.forEach(function (toast) {
    setTimeout(function () {
      dismissToast(toast);
    }, 3000);
  });
  // Restore saved accessibility preferences on load
  initAccessibilityModes();
  setupAccessibilityKeyboardHotkeys();
  setupLiveAriaRegion();
  setupFormSpeechFeedback();
});

// Live Screen Reader Announcement Engine
function announceToScreenReader(message, priority = 'polite') {
  let liveRegion = document.getElementById('sr-live-region');
  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'sr-live-region';
    liveRegion.className = 'sr-only';
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.setAttribute('aria-atomic', 'true');
    document.body.appendChild(liveRegion);
  }
  liveRegion.textContent = message;
}

function setupLiveAriaRegion() {
  if (!document.getElementById('sr-live-region')) {
    const liveRegion = document.createElement('div');
    liveRegion.id = 'sr-live-region';
    liveRegion.className = 'sr-only';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    document.body.appendChild(liveRegion);
  }
}

function dismissToast(toastEl) {
  if (!toastEl || toastEl.classList.contains('dismissing')) return;
  toastEl.classList.add('dismissing');
  toastEl.style.animation = 'toastSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards';
  setTimeout(function () {
    if (toastEl.parentElement) {
      toastEl.remove();
    }
  }, 400);
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-messages-container');
  announceToScreenReader(`${type.toUpperCase()}: ${message}`);
  
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast-message-item alert-${type}`;
  toast.setAttribute('role', 'alert');

  let icon = 'ℹ';
  if (type === 'success') icon = '✓';
  else if (type === 'error' || type === 'danger') icon = '✕';

  toast.innerHTML = `
    <div class="toast-message-content">
      <span class="toast-icon">${icon}</span>
      <span class="toast-text">${message}</span>
    </div>
    <button type="button" class="toast-close-btn" onclick="dismissToast(this.parentElement)" aria-label="Close notification">&times;</button>
    <div class="toast-progress-bar"></div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    dismissToast(toast);
  }, 3200);
}

// 2. Blind Mode Audio Speech Synthesis Engine
let speechEnabled = false;
let speechThrottleTimeout = null;

function speakText(text, priority = false) {
  if (!('speechSynthesis' in window)) return;
  // STRICT ACCESSIBILITY POLICY: Audio speech narration is NEVER spoken unless explicitly toggled ON by user
  if (!speechEnabled) return;

  try {
    window.speechSynthesis.cancel(); // Stop prior narration immediately
    const cleanText = text.trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.error('Speech synthesis error:', e);
  }
}

function enableSpeechMode() {
  if (!speechEnabled) {
    speechEnabled = true;
    document.documentElement.classList.add('access-blind-mode');
    setupBlindModeListeners();
    try {
      const saved = JSON.parse(localStorage.getItem('gtfp-access-modes') || '{}');
      saved['access-blind-mode'] = true;
      localStorage.setItem('gtfp-access-modes', JSON.stringify(saved));
    } catch (e) {}
    syncAccessibilityButtons();
    showToast('Audio Speech Assist automatically activated.', 'info');
  }
}

// Real-Time Assistive Selection & Input Feedback Capsule (Active even when Voice/Audio is OFF)
let assistiveFeedbackTimeout = null;

function showAssistiveInputFeedback(message) {
  if (!message) return;

  // 1. Update native ARIA live region for screen readers (NVDA/JAWS/VoiceOver/Narrator)
  announceToScreenReader(message, 'polite');

  // 2. If voice synthesis mode is on, speak it
  if (speechEnabled) {
    speakText(message);
  }

  // 3. Visual Assistive Feedback Capsule Dock (Always active even with voice off)
  let dock = document.getElementById('assistive-input-indicator');
  if (!dock) {
    dock = document.createElement('div');
    dock.id = 'assistive-input-indicator';
    dock.style.cssText = `
      position: fixed;
      bottom: 24px;
      left: 24px;
      background: #09090B;
      color: #FFFFFF;
      border: 1.5px solid rgba(255, 255, 255, 0.22);
      border-radius: 9999px;
      padding: 8px 18px;
      font-size: 0.82rem;
      font-weight: 700;
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 99999999;
      pointer-events: none;
      transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1), transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      opacity: 0;
      transform: translateY(12px);
      font-family: system-ui, -apple-system, sans-serif;
    `;
    document.body.appendChild(dock);
  }

  dock.innerHTML = `
    <span style="color: #10B981; font-size: 1rem; font-weight: 900;">✓</span>
    <span>${message}</span>
  `;

  dock.style.opacity = '1';
  dock.style.transform = 'translateY(0)';

  clearTimeout(assistiveFeedbackTimeout);
  assistiveFeedbackTimeout = setTimeout(() => {
    dock.style.opacity = '0';
    dock.style.transform = 'translateY(12px)';
  }, 3200);
}

function setupFormSpeechFeedback() {
  const formInputs = document.querySelectorAll('input, select, textarea');
  let typingDebounceTimeout = null;

  function getFieldHumanLabel(input) {
    const fieldName = (input.name || input.id || input.placeholder || '').toLowerCase();
    if (fieldName.includes('name')) return 'Full Name';
    if (fieldName.includes('phone')) return 'Phone Number';
    if (fieldName.includes('email')) return 'Email Address';
    if (fieldName.includes('subject')) return 'Subject';
    if (fieldName.includes('service')) return 'Consultation Service';
    if (fieldName.includes('comm')) return 'Communication Mode';
    if (fieldName.includes('message') || fieldName.includes('quote')) return 'Message Details';
    if (fieldName.includes('search')) return 'Search Query';
    if (fieldName.includes('ref')) return 'Reference Key';
    return input.getAttribute('aria-label') || 'Input Field';
  }

  formInputs.forEach(input => {
    // Focus assistance
    input.addEventListener('focus', function(e) {
      const label = getFieldHumanLabel(input);
      const val = (input.value || '').trim();
      if (speechEnabled) {
        speakText(`Focused ${label}. ${val ? 'Current value is ' + val : 'Field is empty.'}`);
      }
    });

    // Debounced input confirmation when typing (even with voice off, visually confirms)
    input.addEventListener('input', function(e) {
      clearTimeout(typingDebounceTimeout);
      const val = (input.value || '').trim();
      if (!val) return;

      typingDebounceTimeout = setTimeout(() => {
        const label = getFieldHumanLabel(input);
        const displayVal = input.type === 'password' ? '••••••••' : val;
        showAssistiveInputFeedback(`Filled ${label}: ${displayVal}`);
      }, 750);
    });

    // Change / Selection event (dropdown, radio, checkbox, blur)
    input.addEventListener('change', function(e) {
      clearTimeout(typingDebounceTimeout);
      const label = getFieldHumanLabel(input);
      let displayVal = (input.value || '').trim();

      if (input.tagName.toLowerCase() === 'select' && input.selectedIndex >= 0) {
        displayVal = input.options[input.selectedIndex].text.trim();
        showAssistiveInputFeedback(`Selected ${label}: ${displayVal}`);
      } else if (input.type === 'checkbox') {
        const state = input.checked ? 'Checked' : 'Unchecked';
        showAssistiveInputFeedback(`${label}: ${state}`);
      } else if (input.type === 'radio' && input.checked) {
        const parentLabel = input.closest('label') ? input.closest('label').innerText.trim() : displayVal;
        showAssistiveInputFeedback(`Selected: ${parentLabel}`);
      } else if (displayVal) {
        showAssistiveInputFeedback(`Filled ${label}: ${displayVal}`);
      }
    });
  });
}

function setupBlindModeListeners() {
  document.removeEventListener('focusin', handleElementNarration);
  document.removeEventListener('mouseover', handleElementNarration);

  if (speechEnabled) {
    document.addEventListener('focusin', handleElementNarration, true);
    document.addEventListener('mouseover', handleElementNarration, true);
  }
}

function handleElementNarration(e) {
  if (!speechEnabled) return;
  
  // Exclude section / article containers so typing never restarts reading from top to bottom
  const target = e.target.closest('a, button, input, select, textarea, h1, h2, h3, h4, p, img, li');
  if (!target) return;

  // Don't interrupt if user is actively typing in an input/textarea
  if (['input', 'textarea'].includes(document.activeElement.tagName.toLowerCase()) && target !== document.activeElement) {
    return;
  }

  clearTimeout(speechThrottleTimeout);
  speechThrottleTimeout = setTimeout(() => {
    let narration = '';
    const tagName = target.tagName.toLowerCase();

    if (tagName === 'a') {
      narration = `Link: ${target.innerText || target.getAttribute('aria-label') || target.title || 'Navigation link'}`;
    } else if (tagName === 'button') {
      narration = `Button: ${target.innerText || target.getAttribute('aria-label') || target.title || 'Action button'}`;
    } else if (tagName === 'img') {
      narration = `Image: ${target.alt || target.title || 'Graphic visual'}`;
    } else if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
      // Inputs handle their own speech narration on focus/input/change
      return;
    } else if (['h1', 'h2', 'h3', 'h4'].includes(tagName)) {
      narration = `Heading: ${target.innerText}`;
    } else if (tagName === 'p') {
      narration = `Paragraph: ${target.innerText}`;
    } else if (tagName === 'li') {
      narration = `Item: ${target.innerText}`;
    }

    narration = (narration || '').replace(/\s+/g, ' ').trim();

    if (narration && narration.length <= 800) {
      speakText(narration);
    }
  }, 150);
}

// 3. Floating Accessibility Control Console & Keyboard Focus Trap Manager
const ACCESS_MODES = [
  { id: 'access-btn-blind', class: 'access-blind-mode', label: 'Blind / Speech Assist' },
  { id: 'access-btn-contrast', class: 'access-high-contrast', label: 'High Contrast' },
  { id: 'access-btn-text', class: 'access-large-text', label: 'Larger Text' },
  { id: 'access-btn-spacing', class: 'access-text-spaced', label: 'Text Spacing' },
  { id: 'access-btn-font', class: 'access-readable-font', label: 'Readable Font' },
  { id: 'access-btn-links', class: 'access-highlight-links', label: 'Highlight Links' },
  { id: 'access-btn-motion', class: 'access-reduced-motion', label: 'Reduced Motion' }
];

let previousActiveElement = null;

function trapFocus(containerEl) {
  if (!containerEl) return;
  previousActiveElement = document.activeElement;

  const focusables = containerEl.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (focusables.length === 0) return;

  const firstEl = focusables[0];
  const lastEl = focusables[focusables.length - 1];

  firstEl.focus();

  containerEl.onkeydown = function (e) {
    if (e.key === 'Tab') {
      if (e.shiftKey) {
        if (document.activeElement === firstEl) {
          e.preventDefault();
          lastEl.focus();
        }
      } else {
        if (document.activeElement === lastEl) {
          e.preventDefault();
          firstEl.focus();
        }
      }
    } else if (e.key === 'Escape') {
      closeAccessibilityPanel();
      if (previousActiveElement) previousActiveElement.focus();
    }
  };
}

function toggleAccessibilityPanel() {
  const panel = document.getElementById('accessibility-panel');
  if (panel) {
    const isActive = panel.classList.toggle('active');
    if (isActive) {
      announceToScreenReader("Accessibility menu opened. Press Alt plus A to close.");
      trapFocus(panel);
    } else {
      announceToScreenReader("Accessibility menu closed.");
      if (previousActiveElement) previousActiveElement.focus();
    }
  }
}

function closeAccessibilityPanel() {
  const panel = document.getElementById('accessibility-panel');
  if (panel && panel.classList.contains('active')) {
    panel.classList.remove('active');
    announceToScreenReader("Accessibility menu closed.");
    if (previousActiveElement) previousActiveElement.focus();
  }
}

function setupAccessibilityKeyboardHotkeys() {
  document.addEventListener('keydown', function (e) {
    // Alt + A: Open/Close Accessibility Console
    if (e.altKey && (e.key === 'a' || e.key === 'A')) {
      e.preventDefault();
      toggleAccessibilityPanel();
    }
    // Alt + H: Toggle High Contrast Mode
    else if (e.altKey && (e.key === 'h' || e.key === 'H')) {
      e.preventDefault();
      toggleAccessMode('access-high-contrast', 'High Contrast Mode');
    }
    // Alt + S: Toggle Speech Assist / Blind Mode
    else if (e.altKey && (e.key === 's' || e.key === 'S')) {
      e.preventDefault();
      toggleAccessMode('access-blind-mode', 'Blind & Audio Speech Assist');
    }
    // Escape key closes any active panel
    else if (e.key === 'Escape') {
      closeAccessibilityPanel();
    }
  });
}

function toggleAccessMode(modeClass, modeLabel) {
  const html = document.documentElement;
  const isEnabled = html.classList.toggle(modeClass);

  if (modeClass === 'access-blind-mode') {
    speechEnabled = isEnabled;
    setupBlindModeListeners();
    if (isEnabled) {
      speakText("Blind accessibility mode enabled. Hover or navigate through elements to listen.", true);
    } else {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
      speakText("Blind mode disabled.", true);
    }
  }

  try {
    const saved = JSON.parse(localStorage.getItem('gtfp-access-modes') || '{}');
    saved[modeClass] = isEnabled;
    localStorage.setItem('gtfp-access-modes', JSON.stringify(saved));
  } catch (e) {
    console.error('Failed to save accessibility preference:', e);
  }

  syncAccessibilityButtons();

  if (isEnabled) {
    showToast(`${modeLabel} activated.`, 'success');
  } else {
    showToast(`${modeLabel} turned off.`, 'info');
  }
}

function cycleColorblindFilter(filterClass) {
  const html = document.documentElement;
  const filterClasses = [
    'access-colorblind-protanopia',
    'access-colorblind-deuteranopia',
    'access-colorblind-tritanopia',
    'access-colorblind-monochrome'
  ];

  filterClasses.forEach(cls => html.classList.remove(cls));

  if (filterClass && filterClass !== 'off') {
    html.classList.add(filterClass);
    showToast(`Color vision accessibility preset updated to ${filterClass.replace('access-colorblind-', '')}.`, 'info');
  } else {
    showToast('Colorblind filter disabled.', 'info');
  }

  try {
    localStorage.setItem('gtfp-colorblind-mode', filterClass || 'off');
  } catch(e) {}

  const select = document.getElementById('colorblind-select');
  if (select) select.value = filterClass || 'off';
  syncAccessibilityButtons();
}

// 4. Text Alternatives — Visual Image Alt-Text Badge Overlay Toggle
let altOverlayActive = false;

function toggleAltTextOverlay() {
  altOverlayActive = !altOverlayActive;
  const images = document.querySelectorAll('img');
  const statusEl = document.getElementById('alt-overlay-status');

  images.forEach(img => {
    let overlay = img.parentElement.querySelector('.alt-text-badge-overlay');
    if (altOverlayActive) {
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'alt-text-badge-overlay';
        overlay.style.cssText = 'position: absolute; bottom: 4px; left: 4px; background: rgba(0,0,0,0.85); color: #F5D77F; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; z-index: 1000; font-family: sans-serif; pointer-events: none; border: 1px solid #D4AF37;';
        overlay.textContent = `[Alt]: ${img.alt || 'Decorative / No Alt'}`;
        if (img.parentElement && getComputedStyle(img.parentElement).position === 'static') {
          img.parentElement.style.position = 'relative';
        }
        img.parentElement.appendChild(overlay);
      }
      overlay.style.display = 'block';
    } else {
      if (overlay) overlay.style.display = 'none';
    }
  });

  if (statusEl) statusEl.textContent = altOverlayActive ? 'ON' : 'OFF';

  if (altOverlayActive) {
    showToast('Visual Alt-Text Overlay activated.', 'success');
  } else {
    showToast('Visual Alt-Text Overlay turned off.', 'info');
  }
}

// 5. Multimedia Transcripts Modal Control
function openMultimediaTranscripts() {
  const modal = document.getElementById('multimedia-transcripts-modal');
  if (modal) {
    modal.style.display = 'flex';
    announceToScreenReader('Multimedia Transcripts modal opened.');
  }
}

function closeMultimediaTranscripts() {
  const modal = document.getElementById('multimedia-transcripts-modal');
  if (modal) {
    modal.style.display = 'none';
    announceToScreenReader('Multimedia Transcripts modal closed.');
  }
}

function resetAccessibilityModes() {
  const html = document.documentElement;
  ACCESS_MODES.forEach(mode => {
    html.classList.remove(mode.class);
  });

  const filterClasses = [
    'access-colorblind-protanopia',
    'access-colorblind-deuteranopia',
    'access-colorblind-tritanopia',
    'access-colorblind-monochrome'
  ];
  filterClasses.forEach(cls => html.classList.remove(cls));

  const colorblindSelect = document.getElementById('colorblind-select');
  if (colorblindSelect) {
    colorblindSelect.value = 'off';
  }

  speechEnabled = false;
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  setupBlindModeListeners();

  try {
    localStorage.removeItem('gtfp-access-modes');
    localStorage.removeItem('gtfp-colorblind-mode');
  } catch (e) {}

  syncAccessibilityButtons();
  showToast('All accessibility modes reset to default.', 'info');
  speakText("All accessibility modes have been reset to default.", true);
}

function syncAccessibilityButtons() {
  const html = document.documentElement;
  let activeCount = 0;

  ACCESS_MODES.forEach(mode => {
    const btn = document.getElementById(mode.id);
    const isModeActive = html.classList.contains(mode.class);

    if (isModeActive) activeCount++;

    if (btn) {
      const statusText = btn.querySelector('.accessibility-status-text');
      if (isModeActive) {
        btn.classList.add('active');
        if (statusText) statusText.textContent = 'ON';
      } else {
        btn.classList.remove('active');
        if (statusText) statusText.textContent = 'OFF';
      }
    }
  });

  const colorblindSelect = document.getElementById('colorblind-select');
  if (colorblindSelect) {
    let activeFilter = 'off';
    const filterClasses = [
      'access-colorblind-protanopia',
      'access-colorblind-deuteranopia',
      'access-colorblind-tritanopia',
      'access-colorblind-monochrome'
    ];
    for (const cls of filterClasses) {
      if (html.classList.contains(cls)) {
        activeFilter = cls;
        break;
      }
    }
    colorblindSelect.value = activeFilter;
    if (activeFilter !== 'off') activeCount++;
  }

  const badge = document.getElementById('accessibility-active-badge');
  if (badge) {
    if (activeCount > 0) {
      badge.textContent = activeCount;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  }
}

function initAccessibilityModes() {
  try {
    const saved = JSON.parse(localStorage.getItem('gtfp-access-modes') || '{}');
    const html = document.documentElement;
    ACCESS_MODES.forEach(mode => {
      if (saved[mode.class]) {
        html.classList.add(mode.class);
        if (mode.class === 'access-blind-mode') {
          speechEnabled = true;
          setupBlindModeListeners();
        }
      }
    });

    const savedFilter = localStorage.getItem('gtfp-colorblind-mode');
    if (savedFilter && savedFilter !== 'off') {
      html.classList.add(savedFilter);
      const selectEl = document.getElementById('colorblind-select');
      if (selectEl) {
        selectEl.value = savedFilter;
      }
    }

    const filterSelect = document.getElementById('colorblind-select');
    if (filterSelect) filterSelect.value = savedFilter || 'off';

    syncAccessibilityButtons();
  } catch (e) {
    console.error('Failed to restore accessibility preferences:', e);
  }
}

document.addEventListener('click', function (e) {
  const widget = document.getElementById('accessibility-widget');
  const panel = document.getElementById('accessibility-panel');
  if (widget && panel && panel.classList.contains('active')) {
    if (!widget.contains(e.target)) {
      closeAccessibilityPanel();
    }
  }
});

// Explicit Global Window Attachments for Guaranteed Inline Execution
window.toggleAccessibilityPanel = toggleAccessibilityPanel;
window.closeAccessibilityPanel = closeAccessibilityPanel;
window.toggleAccessMode = toggleAccessMode;
window.resetAccessibilityModes = resetAccessibilityModes;
window.cycleColorblindFilter = cycleColorblindFilter;
window.changeColorblindMode = cycleColorblindFilter;
window.openMultimediaTranscripts = openMultimediaTranscripts;
window.closeMultimediaTranscripts = closeMultimediaTranscripts;
window.enableSpeechMode = enableSpeechMode;
window.speakText = speakText;
window.announceToScreenReader = announceToScreenReader;
window.showAssistiveInputFeedback = showAssistiveInputFeedback;

