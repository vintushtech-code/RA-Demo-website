/**
 * GuardianTree FP — Consultation Scheduling Engine & Calendar Logic
 * Handles dynamic calendar day rendering, weekend/past validations, duration switching,
 * slot fetching from server API, AJAX booking submission, and real-time tracking lookup.
 */

// State Management
let currentYear, currentMonth;
let selectedDateStr = "";
let selectedDuration = 45;
let selectedTimeStr = "";
let selectedTimeDisplay = "";
let selectedEndTimeDisplay = "";

function getSlotsApiUrl() {
  return window.SLOTS_API_URL || '/consultation/slots/';
}

function getTrackApiUrl() {
  return window.TRACK_API_URL || '/consultation/api/track/';
}


document.addEventListener('DOMContentLoaded', function () {
  // Ensure document scroll is fully unlocked and modals are dismissed
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
  closeValidationModal();

  if (window.DEFAULT_DATE) selectedDateStr = window.DEFAULT_DATE;
  if (window.DEFAULT_DURATION) selectedDuration = window.DEFAULT_DURATION;
  
  // Read initial data from HTML data attributes if available
  const hubSection = document.getElementById('booking-hub') || document.querySelector('.consultation-page');
  if (hubSection) {
    if (!selectedDateStr) selectedDateStr = hubSection.getAttribute('data-default-date') || selectedDateStr;
    const durAttr = hubSection.getAttribute('data-default-duration');
    if (durAttr && !window.DEFAULT_DURATION) selectedDuration = parseInt(durAttr) || 45;
  }

  // Initialize date object
  const initDate = selectedDateStr ? new Date(selectedDateStr + 'T00:00:00') : new Date();
  currentYear = initDate.getFullYear();
  currentMonth = initDate.getMonth();

  renderCalendar(currentYear, currentMonth);
  if (selectedDateStr) {
    fetchAvailableSlots(selectedDateStr, selectedDuration);
  }
  applyConsultationPrefillFromUrl();
});

/* --------------------------------------------------------------------------
   1. Interactive Calendar Renderer
   -------------------------------------------------------------------------- */
function renderCalendar(year, month) {
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const monthTitle = document.getElementById('calendar-month-year');
  if (monthTitle) {
    monthTitle.textContent = `${monthNames[month]} ${year}`;
  }

  const grid = document.getElementById('calendar-days-grid');
  if (!grid) return;
  grid.innerHTML = '';

  const firstDayIndex = new Date(year, month, 1).getDay(); // 0 is Sunday
  // Shift Sunday (0) to index 6, Monday (1) to index 0
  const startOffset = (firstDayIndex === 0) ? 6 : firstDayIndex - 1;

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Render empty prefix cells
  for (let i = 0; i < startOffset; i++) {
    const emptyCell = document.createElement('div');
    emptyCell.className = 'calendar-day-btn empty';
    grid.appendChild(emptyCell);
  }

  // Render days in active month
  for (let day = 1; day <= daysInMonth; day++) {
    const dateObj = new Date(year, month, day);
    dateObj.setHours(0, 0, 0, 0);

    const dayOfWeek = dateObj.getDay(); // 0 = Sun, 6 = Sat
    const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);
    const isPast = dateObj < today;
    const isToday = dateObj.getTime() === today.getTime();

    const yyyy = year;
    const mm = String(month + 1).padStart(2, '0');
    const dd = String(day).padStart(2, '0');
    const dateStr = `${yyyy}-${mm}-${dd}`;

    const isSelected = (dateStr === selectedDateStr);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'calendar-day-btn';
    btn.textContent = day;
    btn.setAttribute('data-date', dateStr);

    if (isToday) btn.classList.add('today');
    if (isSelected) btn.classList.add('selected');

    if (isWeekend) {
      btn.classList.add('weekend');
      btn.disabled = true;
      btn.title = "Advisory Desk Closed on Weekends";
    } else if (isPast) {
      btn.classList.add('past');
      btn.disabled = true;
      btn.title = "Past Date Unavailable";
    } else {
      btn.addEventListener('click', function () {
        selectDate(dateStr, dateObj);
      });
    }

    grid.appendChild(btn);
  }
}

function prevMonth() {
  currentMonth--;
  if (currentMonth < 0) {
    currentMonth = 11;
    currentYear--;
  }
  renderCalendar(currentYear, currentMonth);
}

function nextMonth() {
  currentMonth++;
  if (currentMonth > 11) {
    currentMonth = 0;
    currentYear++;
  }
  renderCalendar(currentYear, currentMonth);
}

function selectDate(dateStr, dateObj) {
  selectedDateStr = dateStr;

  // Update hidden field
  const dateInput = document.getElementById('id_consultation_date');
  if (dateInput) dateInput.value = dateStr;

  // Update active highlight in calendar
  document.querySelectorAll('.calendar-day-btn').forEach(btn => {
    btn.classList.remove('selected');
    if (btn.getAttribute('data-date') === dateStr) {
      btn.classList.add('selected');
    }
  });

  // Format human readable date
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const displayDate = dateObj.toLocaleDateString('en-US', options);

  const infoBarText = document.getElementById('calendar-selected-date-text');
  if (infoBarText) infoBarText.textContent = displayDate;

  updateSummaryCard();
  fetchAvailableSlots(dateStr, selectedDuration);

  if (typeof speakText === 'function') {
    speakText(`You selected business date: ${displayDate}`);
  }
}

/* --------------------------------------------------------------------------
   2. Duration Selection
   -------------------------------------------------------------------------- */
function selectDuration(dur) {
  selectedDuration = parseInt(dur);

  const durationInput = document.getElementById('id_duration_minutes');
  if (durationInput) durationInput.value = selectedDuration;

  document.querySelectorAll('.duration-card-item').forEach(card => {
    card.classList.remove('selected');
    if (parseInt(card.getAttribute('data-duration')) === selectedDuration) {
      card.classList.add('selected');
    }
  });

  updateSummaryCard();
  if (selectedDateStr) {
    fetchAvailableSlots(selectedDateStr, selectedDuration);
  }

  if (typeof speakText === 'function') {
    speakText(`You selected consultation duration: ${dur} minutes`);
  }
}

/* --------------------------------------------------------------------------
   3. Fetch Dynamic Available Slots via Server API
   -------------------------------------------------------------------------- */
function fetchAvailableSlots(dateStr, duration) {
  const slotsGrid = document.getElementById('time-slots-grid');
  const slotsMeta = document.getElementById('slots-count-meta');
  if (!slotsGrid) return;

  slotsGrid.innerHTML = `
    <div class="time-slots-empty-state">
      <i class="fa-solid fa-spinner fa-spin" style="color: var(--c-gold, #D4AF37); margin-right: 6px;"></i> 
      Calculating available 15-min buffered slots...
    </div>
  `;

  const slotsUrl = `${getSlotsApiUrl()}?date=${dateStr}&duration=${duration}`;

  fetch(slotsUrl)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'weekend') {
        slotsGrid.innerHTML = `
          <div class="time-slots-empty-state" style="color: #94A3B8;">
            <i class="fa-regular fa-calendar-xmark" style="font-size: 1.3rem; margin-bottom: 6px; display: block;"></i>
            ${data.message}
          </div>
        `;
        if (slotsMeta) slotsMeta.textContent = '0 slots';
        return;
      }

      if (data.status !== 'success' || !data.slots || data.slots.length === 0) {
        slotsGrid.innerHTML = `
          <div class="time-slots-empty-state">
            <i class="fa-solid fa-circle-info" style="font-size: 1.2rem; margin-bottom: 6px; display: block; color: var(--c-gold, #D4AF37);"></i>
            No consultation times are available for this date.<br>
            <strong>Please choose another date.</strong>
          </div>
        `;
        if (slotsMeta) slotsMeta.textContent = '0 available';
        return;
      }

      slotsGrid.innerHTML = '';
      let foundDefault = false;

      data.slots.forEach(slot => {
        const slotBtn = document.createElement('button');
        slotBtn.type = 'button';
        slotBtn.className = 'time-slot-btn';
        slotBtn.setAttribute('data-time', slot.time);
        slotBtn.setAttribute('data-time-display', slot.time_display);
        slotBtn.setAttribute('data-end-display', slot.end_time_display);

        if (!slot.is_available) {
          slotBtn.classList.add('disabled');
          if (slot.is_booked) slotBtn.classList.add('booked');
          slotBtn.disabled = true;
          slotBtn.innerHTML = `
            <span class="slot-time-primary">${slot.time_display}</span>
            <span class="slot-booked-tag">${slot.reason}</span>
          `;
        } else {
          // Highlight only if previously selected by user
          const isMatch = Boolean(selectedTimeStr && slot.time === selectedTimeStr);
          if (isMatch) {
            slotBtn.classList.add('selected');
            selectedTimeStr = slot.time;
            selectedTimeDisplay = slot.time_display;
            selectedEndTimeDisplay = slot.end_time_display;
            foundDefault = true;

            const timeInput = document.getElementById('id_consultation_time');
            if (timeInput) timeInput.value = slot.time;
          }

          slotBtn.innerHTML = `
            <span class="slot-time-primary">${slot.time_display}</span>
            <span class="slot-time-sub">to ${slot.end_time_display}</span>
          `;

          slotBtn.addEventListener('click', function () {
            document.querySelectorAll('.time-slot-btn').forEach(b => b.classList.remove('selected'));
            slotBtn.classList.add('selected');
            selectedTimeStr = slot.time;
            selectedTimeDisplay = slot.time_display;
            selectedEndTimeDisplay = slot.end_time_display;

            const timeInput = document.getElementById('id_consultation_time');
            if (timeInput) timeInput.value = slot.time;

            updateSummaryCard();

            if (typeof speakText === 'function') {
              speakText(`You selected time slot: ${slot.time_display} to ${slot.end_time_display}`);
            }
          });
        }

        slotsGrid.appendChild(slotBtn);
      });

      if (slotsMeta) {
        slotsMeta.textContent = `${data.available_count} available (${data.duration}m)`;
      }

      updateSummaryCard();
    })
    .catch(() => {
      slotsGrid.innerHTML = `
        <div class="time-slots-empty-state" style="color: #DC2626;">
          Unable to connect to slot scheduling server. Please try again.
        </div>
      `;
    });
}

const DURATION_FEES = {
  30: { fee: 3000, display: '₹3,000 INR', label: '30 Minutes (Focused Consultation)' },
  45: { fee: 5000, display: '₹5,000 INR', label: '45 Minutes (Strategic Consultation)' },
  60: { fee: 8000, display: '₹8,000 INR', label: '60 Minutes (Comprehensive Consultation)' }
};

/* --------------------------------------------------------------------------
   4. Update Live Dynamic Booking Summary Card
   -------------------------------------------------------------------------- */
function updateSummaryCard() {
  // Progress Bar Logic
  const bar = document.getElementById('progress-bar-fill');
  if (bar) {
    document.querySelectorAll('.progress-step-label').forEach(el => el.classList.remove('active'));
    let step = 1;
    let width = '33%';
    if (selectedDateStr) {
      step = 2;
      width = '66%';
    }
    if (selectedTimeStr) {
      step = 3;
      width = '100%';
    }
    bar.style.width = width;
    const activeLabel = document.getElementById('label-step-' + step);
    if (activeLabel) activeLabel.classList.add('active');
  }

  // Service
  const serviceSelect = document.getElementById('id_service');
  const serviceSummary = document.getElementById('summary-service-text');
  if (serviceSelect && serviceSummary && serviceSelect.selectedIndex >= 0) {
    serviceSummary.textContent = serviceSelect.options[serviceSelect.selectedIndex].text;
  }

  // Duration & Advisory Fee (₹3,000 for 30m, ₹5,000 for 45m, ₹8,000 for 60m)
  const durationSummary = document.getElementById('summary-duration-text');
  const feeSummary = document.getElementById('summary-fee-text');
  const feeInfo = DURATION_FEES[selectedDuration] || DURATION_FEES[45];
  
  if (durationSummary) {
    durationSummary.textContent = feeInfo.label;
  }
  if (feeSummary) {
    feeSummary.textContent = feeInfo.display;
  }

  // Date & Time
  const infoBarText = document.getElementById('calendar-selected-date-text');
  const dateSummary = document.getElementById('summary-date-text');
  const datetimeSummary = document.getElementById('summary-datetime-text');
  const timeSummary = document.getElementById('summary-time-text');
  
  const dateLabel = (infoBarText ? infoBarText.textContent : (selectedDateStr || 'Tuesday, 18 August 2026'));
  const timeLabel = selectedTimeDisplay ? `${selectedTimeDisplay} – ${selectedEndTimeDisplay}` : '10:00 AM – 10:45 AM';

  if (dateSummary) dateSummary.textContent = dateLabel;
  if (timeSummary) timeSummary.textContent = timeLabel;
  if (datetimeSummary) datetimeSummary.textContent = `${dateLabel} at ${selectedTimeDisplay || '10:00 AM'}`;
}

function getUrlParameter(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || '';
}

function applyConsultationPrefillFromUrl() {
  const name = getUrlParameter('client_name');
  const email = getUrlParameter('email');
  const service = getUrlParameter('service');
  const subject = getUrlParameter('subject');
  const message = getUrlParameter('message');
  const key = getUrlParameter('key') || getUrlParameter('confirmed_key') || getUrlParameter('ref');

  if (name) {
    const nameField = document.getElementById('id_client_name');
    if (nameField) nameField.value = decodeURIComponent(name);
  }
  if (email) {
    const emailField = document.getElementById('id_email');
    if (emailField) emailField.value = decodeURIComponent(email);
  }
  if (service) {
    const serviceSelect = document.getElementById('id_service');
    if (serviceSelect) {
      for (let i = 0; i < serviceSelect.options.length; i++) {
        if (serviceSelect.options[i].value === service) {
          serviceSelect.selectedIndex = i;
          break;
        }
      }
    }
  }
  if (subject) {
    const subjectField = document.getElementById('id_subject');
    if (subjectField) subjectField.value = decodeURIComponent(subject);
  }
  if (message) {
    const messageField = document.getElementById('id_message');
    if (messageField) messageField.value = decodeURIComponent(message);
  }

  // Handle prefill of reference key
  const confKeyFromDom = document.getElementById('display-reference-key')?.textContent?.trim();
  const effectiveRefKey = key || ((confKeyFromDom && confKeyFromDom !== 'GT7K4M9P2X') ? confKeyFromDom : '');

  if (effectiveRefKey) {
    const cleanKey = effectiveRefKey.trim().toUpperCase();
    const trackInput = document.getElementById('track-reference-key-input');
    if (trackInput && (!trackInput.value || trackInput.value === 'GT7K4M9P2X')) {
      trackInput.value = cleanKey;
    }
    const trackBtn = document.getElementById('btn-track-confirmed-booking');
    if (trackBtn) {
      trackBtn.setAttribute('data-ref-key', cleanKey);
    }
    const rcptKey = document.getElementById('rcpt-ref-key');
    if (rcptKey && (!rcptKey.textContent || rcptKey.textContent.trim() === 'GT7K4M9P2X')) {
      rcptKey.textContent = cleanKey;
    }
  }

  updateSummaryCard();
}

/* --------------------------------------------------------------------------
   5. Required Fields Validation Modal Popup & Form Submission
   -------------------------------------------------------------------------- */
function showValidationModal(errorsArray, focusTargetId) {
  const modal = document.getElementById('consultation-validation-modal');
  const listEl = document.getElementById('validation-errors-list');
  
  if (!modal || !listEl) {
    alert("Please complete the required fields:\n" + errorsArray.join("\n"));
    return;
  }
  
  let html = '<ul style="margin: 0; padding-left: 1.2rem; line-height: 1.7; font-weight: 500;">';
  errorsArray.forEach(err => {
    html += `<li style="margin-bottom: 4px;">${err}</li>`;
  });
  html += '</ul>';
  listEl.innerHTML = html;
  
  modal.style.display = 'flex';
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
  document.documentElement.style.overflow = 'hidden';

  if (focusTargetId) {
    const targetEl = document.getElementById(focusTargetId);
    if (targetEl) {
      setTimeout(() => {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (targetEl.focus && typeof targetEl.focus === 'function') {
          try { targetEl.focus(); } catch (e) {}
        }
      }, 300);
    }
  }
}

function closeValidationModal() {
  const modal = document.getElementById('consultation-validation-modal');
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
}

function handleBookingSubmit(event) {
  if (event) event.preventDefault();
  closeValidationModal();
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
  const form = document.getElementById('consultation-booking-form') || (event ? event.target : null);
  if (!form) return false;

  const clientName = (document.getElementById('id_client_name')?.value || '').trim();
  const email = (document.getElementById('id_email')?.value || '').trim();
  const phone = (document.getElementById('id_phone')?.value || '').trim();
  const dateStr = (document.getElementById('id_consultation_date')?.value || selectedDateStr || '').trim();
  const timeStr = (document.getElementById('id_consultation_time')?.value || selectedTimeStr || '').trim();

  const errors = [];
  let focusTarget = null;

  if (!clientName) {
    errors.push("Full Name is required.");
    if (!focusTarget) focusTarget = 'id_client_name';
  }
  
  if (!email) {
    errors.push("Email Address is required.");
    if (!focusTarget) focusTarget = 'id_email';
  } else if (!email.includes('@') || !email.includes('.')) {
    errors.push("Please enter a valid Email Address (e.g. name@company.com).");
    if (!focusTarget) focusTarget = 'id_email';
  }

  if (!phone) {
    errors.push("Phone Number is required.");
    if (!focusTarget) focusTarget = 'id_phone';
  } else if (phone.length < 5) {
    errors.push("Please enter a valid Phone Number.");
    if (!focusTarget) focusTarget = 'id_phone';
  }

  if (!dateStr) {
    errors.push("Please select a Consultation Date on the calendar (Step 2).");
    if (!focusTarget) focusTarget = 'calendar-days-grid';
  }

  if (!timeStr) {
    errors.push("Please select an available Time Slot (Step 3).");
    if (!focusTarget) focusTarget = 'time-slots-grid';
  }

  if (errors.length > 0) {
    showValidationModal(errors, focusTarget);
    return false;
  }

  const submitBtn = document.getElementById('btn-submit-booking');
  const origBtnHtml = submitBtn ? submitBtn.innerHTML : '';

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Securing Consultation...`;
  }

  const formData = new FormData(form);
  formData.append('ajax', '1');

  fetch(form.action, {
    method: 'POST',
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
    .then(response => response.json())
    .then(data => {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origBtnHtml;
      }

      if (data.status === 'success') {
        // Unlock scroll completely and ensure modals are closed
        closeValidationModal();
        closeReceiptModal();
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';

        // Render Confirmation Card with 10-char Key
        const confCard = document.getElementById('confirmation-card');
        const keyDisplay = document.getElementById('display-reference-key');
        const clientNameDisplay = document.getElementById('conf-client-name');
        const serviceDisplay = document.getElementById('conf-service');
        const dateTimeDisplay = document.getElementById('conf-datetime');
        const durationDisplay = document.getElementById('conf-duration');

        if (keyDisplay) keyDisplay.textContent = data.reference_key;
        if (clientNameDisplay) clientNameDisplay.textContent = data.client_name;
        if (serviceDisplay) serviceDisplay.textContent = data.service;
        if (dateTimeDisplay) dateTimeDisplay.textContent = `${data.date} at ${data.time}`;
        if (durationDisplay) durationDisplay.textContent = data.duration_label;

        if (confCard) {
          confCard.style.display = 'block';
          setTimeout(() => {
            confCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }, 50);
        }

        // Pre-fill tracking lookup and confirmation track button
        const trackBtn = document.getElementById('btn-track-confirmed-booking');
        if (trackBtn) {
          trackBtn.setAttribute('data-ref-key', data.reference_key);
        }

        const trackInput = document.getElementById('track-reference-key-input');
        if (trackInput) {
          trackInput.value = data.reference_key;
        }

        // Pre-fill receipt modal reference key & details
        const rcptKey = document.getElementById('rcpt-ref-key');
        if (rcptKey) rcptKey.textContent = data.reference_key;
        const rcptClientName = document.getElementById('rcpt-client-name');
        if (rcptClientName) rcptClientName.textContent = data.client_name;
        const rcptEmail = document.getElementById('rcpt-client-email');
        if (rcptEmail) rcptEmail.textContent = data.email;
        const rcptService = document.getElementById('rcpt-service-name');
        if (rcptService) rcptService.textContent = data.service;
        const rcptDatetime = document.getElementById('rcpt-datetime');
        if (rcptDatetime) rcptDatetime.textContent = `${data.date} at ${data.time}`;
        const rcptDuration = document.getElementById('rcpt-duration');
        if (rcptDuration) rcptDuration.textContent = data.duration_label;

        // Comprehensive speech narration of confirmed booking & reference key
        if (typeof speakText === 'function') {
          let confMessage = `Consultation request confirmed successfully! `;
          confMessage += `Your unique 10 character booking reference key is ${data.reference_key}. `;
          confMessage += `Booking is registered under the name of ${data.client_name} for ${data.service}. `;
          confMessage += `Scheduled on ${data.date} at ${data.time}. `;
          confMessage += `Duration: ${data.duration_label}. `;
          confMessage += `Current Status: Request Submitted and queued for fiduciary review.`;
          speakText(confMessage);
        }

        // Trigger real-time tracking display
        renderTrackData(data.data);
      } else {
        const serverErrors = [];
        if (data.errors) {
          for (let field in data.errors) {
            serverErrors.push(`• ${field.toUpperCase()}: ${data.errors[field].join(', ')}`);
          }
        } else if (data.message) {
          serverErrors.push(data.message);
        }
        showValidationModal(serverErrors.length ? serverErrors : ["Please review your selections and complete required fields."]);
      }
    })
    .catch(() => {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origBtnHtml;
      }
      form.submit(); // Fallback to normal post
    });
}

/* --------------------------------------------------------------------------
   6. Copy 10-Character Reference Key
   -------------------------------------------------------------------------- */
function copyReferenceKey() {
  const keyEl = document.getElementById('display-reference-key');
  const copyLabel = document.getElementById('copy-btn-label');
  if (!keyEl) return;

  const textToCopy = keyEl.textContent.trim();
  navigator.clipboard.writeText(textToCopy).then(() => {
    if (copyLabel) copyLabel.textContent = 'Copied!';
    setTimeout(() => {
      if (copyLabel) copyLabel.textContent = 'Copy Key';
    }, 2500);
  });
}

/* --------------------------------------------------------------------------
   7. Live Consultation Status Tracking
   -------------------------------------------------------------------------- */
function handleTrackingSearch(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('track-reference-key-input');
  if (!input) return;

  let key = input.value.trim().toUpperCase();
  // Fallback if input is empty or has placeholder
  if (!key || key === 'GT7K4M9P2X') {
    const displayKey = document.getElementById('display-reference-key')?.textContent?.trim().toUpperCase();
    if (displayKey && displayKey.length === 10 && displayKey !== 'GT7K4M9P2X') {
      key = displayKey;
      input.value = key;
    }
  }

  if (key.length !== 10) {
    alert("Please enter a valid 10-character reference key (e.g. GT7K4M9P2X).");
    return;
  }

  const btn = document.getElementById('btn-track-submit');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Searching...`;
  }

  const trackUrl = `${getTrackApiUrl()}?key=${key}`;

  fetch(trackUrl)
    .then(response => response.json())
    .then(res => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }

      if (res.status === 'success' && res.data) {
        renderTrackData(res.data);
        const resultContainer = document.getElementById('tracking-result-container');
        if (resultContainer) {
          resultContainer.style.display = 'block';
          resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      } else {
        alert(res.message || `No consultation record was found matching reference key '${key}'.`);
      }
    })
    .catch(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = origHtml;
      }
      alert("Failed to connect to tracking server. Please verify your reference key.");
    });
}

function lookupSpecificKey(key) {
  let resolvedKey = (typeof key === 'string') ? key.trim().toUpperCase() : '';

  // If key is empty or is placeholder 'GT7K4M9P2X', check DOM elements for the actual booked key
  if (!resolvedKey || resolvedKey === 'GT7K4M9P2X') {
    const displayKey = document.getElementById('display-reference-key')?.textContent?.trim().toUpperCase();
    const btnKey = document.getElementById('btn-track-confirmed-booking')?.getAttribute('data-ref-key')?.trim().toUpperCase();
    const inputKey = document.getElementById('track-reference-key-input')?.value?.trim().toUpperCase();

    if (displayKey && displayKey.length === 10 && displayKey !== 'GT7K4M9P2X') {
      resolvedKey = displayKey;
    } else if (btnKey && btnKey.length === 10 && btnKey !== 'GT7K4M9P2X') {
      resolvedKey = btnKey;
    } else if (inputKey && inputKey.length === 10 && inputKey !== 'GT7K4M9P2X') {
      resolvedKey = inputKey;
    }
  }

  const input = document.getElementById('track-reference-key-input');
  if (input && resolvedKey) {
    input.value = resolvedKey;
  }

  const trackSection = document.getElementById('track-section');
  const resultContainer = document.getElementById('tracking-result-container');

  // If tracking result container already contains data for this key, smoothly scroll to it!
  if (resultContainer && resultContainer.style.display !== 'none' && activeReceiptData && activeReceiptData.reference_key === resolvedKey) {
    resultContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  // Scroll to track section smoothly
  if (trackSection) {
    trackSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // If we resolved a valid 10-char key, execute the lookup search
  if (resolvedKey && resolvedKey.length === 10 && resolvedKey !== 'GT7K4M9P2X') {
    handleTrackingSearch(null);
  }
}

function renderTrackData(data) {
  const container = document.getElementById('tracking-result-container');
  if (!container) return;

  let rescheduledHtml = '';
  if (data.is_rescheduled || data.previous_schedule) {
    rescheduledHtml = `
      <div class="rescheduled-diff-banner">
        <div class="rescheduled-diff-title">
          <i class="fa-solid fa-calendar-days"></i>
          <span>CONSULTATION SCHEDULE REVISION NOTIFICATION</span>
        </div>
        <div class="rescheduled-diff-grid">
          <div class="diff-schedule-box previous">
            <div class="diff-label">Previous Schedule</div>
            <div class="diff-time">${data.previous_schedule || 'Tuesday, 18 August — 10:00 AM'}</div>
          </div>
          <div class="diff-schedule-box updated">
            <div class="diff-label">Updated Schedule</div>
            <div class="diff-time">${data.updated_schedule}</div>
          </div>
        </div>
        <div class="rescheduled-reason-note">
          <strong>Advisory Desk Note:</strong> ${data.rescheduled_reason || 'The schedule was updated by the advisory desk to allocate senior partner boardroom resources.'}
        </div>
      </div>
    `;
  }

  let timelineHtml = '<div class="timeline-stepper" role="list" aria-label="Consultation Status Lifecycle Timeline">';
  if (data.timeline && data.timeline.length) {
    data.timeline.forEach(step => {
      const isCurrent = step.state === 'active' ? 'aria-current="step"' : '';
      timelineHtml += `
        <div class="timeline-step-item ${step.state}" role="listitem" ${isCurrent} aria-label="Step ${step.step}: ${step.title} (${step.state})">
          <div class="timeline-node" aria-hidden="true">${step.step}</div>
          <div class="timeline-label">${step.title}</div>
          <div class="timeline-subtext">${step.description}</div>
        </div>
      `;
    });
  }
  timelineHtml += '</div>';

  if (typeof speakText === 'function') {
    let speechMessage = `Consultation tracking status for reference key ${data.reference_key}. `;
    speechMessage += `Booking is under the name of ${data.client_name}. `;
    speechMessage += `Advisory Service: ${data.service}. `;
    speechMessage += `Current Status: ${data.status_label}. `;
    speechMessage += `Scheduled for ${data.consultation_date} at ${data.consultation_time}. `;
    speechMessage += `Duration: ${data.duration_label}, via ${data.preferred_comm}. `;
    speechMessage += `Payment Status: ${data.payment_status}. Fee: ${data.net_display || data.fee_display || '₹5,000 INR'}. `;

    if (data.is_rescheduled || data.previous_schedule) {
      speechMessage += `Notice: This schedule was revised by the advisory desk from ${data.previous_schedule || 'original time'} to ${data.updated_schedule}. `;
    }

    if (data.timeline && data.timeline.length) {
      const activeStep = data.timeline.find(s => s.state === 'active') || data.timeline.find(s => s.state === 'completed');
      if (activeStep) {
        speechMessage += `Lifecycle Progress: Step ${activeStep.step}, ${activeStep.title} (${activeStep.description}).`;
      }
    }

    speakText(speechMessage);
  }

  if (typeof announceToScreenReader === 'function') {
    announceToScreenReader(`Consultation status found for ${data.reference_key}: ${data.status_label}. Client: ${data.client_name}`);
  }

  container.innerHTML = `
    <div class="tracking-result-box">
      <div class="tracking-result-header">
        <div style="display: flex; align-items: center; gap: 0.85rem; flex-wrap: wrap;">
          <span class="tracking-ref-badge">${data.reference_key}</span>
          <div>
            <strong style="font-size: 1.05rem; color: var(--color-primary);">${data.client_name}</strong>
            <div style="font-size: 0.8rem; color: var(--color-subtext);">${data.service}</div>
          </div>
        </div>
        <span class="tracking-status-pill ${data.status_badge}">${data.status_label}</span>
      </div>

      ${rescheduledHtml}
      ${timelineHtml}

      <div class="confirmation-details-summary" style="margin-bottom: 0;">
        <div class="confirmation-summary-grid">
          <div>
            <div class="consult-summary-item-label">Consultation Schedule</div>
            <div class="consult-summary-item-value">${data.consultation_date} at ${data.consultation_time}</div>
          </div>
          <div>
            <div class="consult-summary-item-label">Duration &amp; Mode</div>
            <div class="consult-summary-item-value">${data.duration_label} (${data.preferred_comm})</div>
          </div>
          <div>
            <div class="consult-summary-item-label">Advisory Fee &amp; Net Due</div>
            <div class="consult-summary-item-value" style="font-weight: 700; color: var(--color-primary);">${data.net_display || data.fee_display || '₹5,000.00'}</div>
          </div>
          <div>
            <div class="consult-summary-item-label">Payment Status</div>
            <div class="consult-summary-item-value" style="font-weight: 700; color: ${data.payment_status_code === 'paid' || data.payment_status_code === 'waived' ? '#059669' : '#dc2626'};">${data.payment_status}</div>
          </div>
        </div>
      </div>

      <div style="margin-top: 1.25rem; display: flex; justify-content: flex-end; gap: 0.75rem; flex-wrap: wrap;">
        <button type="button" class="btn-consult-secondary" style="padding: 0.55rem 1.25rem; font-size: 0.82rem;" onclick="openReceiptModal()">
          <i class="fa-solid fa-file-invoice"></i>
          <span>View &amp; Print Confirmation Statement</span>
        </button>
      </div>
    </div>
  `;

  // Save current data for receipt modal
  activeReceiptData = data;
  container.style.display = 'block';
}

/* --------------------------------------------------------------------------
   8. Executive Consultation Confirmation & Billing Receipt Modal Logic
   -------------------------------------------------------------------------- */
let activeReceiptData = null;

function openReceiptModal(customData) {
  const modal = document.getElementById('consultation-receipt-modal');
  if (!modal) return;

  const data = customData || activeReceiptData || {};

  // Extract fallback values from DOM or state
  const refKey = data.reference_key || document.getElementById('display-reference-key')?.textContent.trim() || document.getElementById('track-reference-key-input')?.value.trim() || 'GT7K4M9P2X';
  const clientName = data.client_name || document.getElementById('conf-client-name')?.textContent.trim() || document.getElementById('id_client_name')?.value.trim() || 'Eleanor Vance';
  const email = data.email || document.getElementById('id_email')?.value.trim() || 'client@advisory.guardiantreefp.com';
  const phone = data.phone || document.getElementById('id_phone')?.value.trim() || '+91 98765 43210';
  const service = data.service || document.getElementById('conf-service')?.textContent.trim() || document.getElementById('id_service')?.selectedOptions?.[0]?.text || 'Investment & Multi-Asset Portfolio Strategy';
  const datetime = (data.consultation_date && data.consultation_time) ? `${data.consultation_date} at ${data.consultation_time}` : (document.getElementById('conf-datetime')?.textContent.trim() || 'Tuesday, 18 August 2026 at 10:00 AM');
  
  const durationMinutes = data.duration_minutes || selectedDuration || 45;
  const feeInfo = DURATION_FEES[durationMinutes] || DURATION_FEES[45];
  const durationLabel = data.duration_label || document.getElementById('conf-duration')?.textContent.trim() || feeInfo.label;
  const channel = data.preferred_comm || document.getElementById('id_preferred_comm')?.selectedOptions?.[0]?.text || 'Secure Video Conference';
  const fiduciaryDesk = data.fiduciary_desk || 'Senior Wealth Advisory Desk';
  
  const feeDisplay = data.fee_display || `₹${feeInfo.fee.toLocaleString('en-IN')}.00`;
  const discountDisplay = data.discount_display ? `-${data.discount_display}` : '-₹0.00';
  const netDisplay = data.net_display || feeDisplay;
  
  const paymentStatus = data.payment_status || (data.payment_status_code === 'paid' ? 'PAID / COMPLETED' : 'UNPAID / PAYMENT DUE');
  const isPaidOrWaived = data.payment_status_code === 'paid' || data.payment_status_code === 'waived' || paymentStatus.toLowerCase().includes('paid') || paymentStatus.toLowerCase().includes('waived');
  const invoiceNumber = data.invoice_number || `INV-${new Date().getFullYear()}-${refKey.slice(0, 6)}`;
  const statusLabel = (data.status_label || 'CONFIRMED & ALLOCATED').toUpperCase();

  // Populate receipt elements
  const elKey = document.getElementById('rcpt-ref-key');
  const elName = document.getElementById('rcpt-client-name');
  const elEmail = document.getElementById('rcpt-client-email');
  const elPhone = document.getElementById('rcpt-client-phone');
  const elService = document.getElementById('rcpt-service-name');
  const elDatetime = document.getElementById('rcpt-datetime');
  const elDuration = document.getElementById('rcpt-duration');
  const elChannel = document.getElementById('rcpt-channel');
  const elDesk = document.getElementById('rcpt-fiduciary-desk');
  const elFee = document.getElementById('rcpt-fee-rate');
  const elDiscount = document.getElementById('rcpt-discount-amount');
  const elNet = document.getElementById('rcpt-net-total');
  const elGrand = document.getElementById('rcpt-grand-total');
  const elPayment = document.getElementById('rcpt-payment-status');
  const elInvoice = document.getElementById('rcpt-invoice-id');
  const elIssueDate = document.getElementById('rcpt-issue-date');
  const elStatusBadge = document.getElementById('rcpt-status-badge-text');
  const elStatusDot = document.getElementById('rcpt-status-dot');
  const elTableDuration = document.getElementById('rcpt-table-duration');

  if (elKey) elKey.textContent = refKey;
  if (elName) elName.textContent = clientName;
  if (elEmail) elEmail.textContent = email;
  if (elPhone) elPhone.textContent = phone;
  if (elService) elService.textContent = service;
  if (elDatetime) elDatetime.textContent = datetime;
  if (elDuration) elDuration.textContent = durationLabel;
  if (elChannel) elChannel.textContent = channel;
  if (elDesk) elDesk.textContent = fiduciaryDesk;
  if (elTableDuration) elTableDuration.textContent = `${durationMinutes} Minutes`;
  if (elFee) elFee.textContent = feeDisplay;
  if (elDiscount) elDiscount.textContent = discountDisplay;
  if (elNet) elNet.textContent = netDisplay;
  
  if (elGrand) {
    elGrand.textContent = `${netDisplay} INR`;
    elGrand.style.color = isPaidOrWaived ? '#059669' : '#dc2626';
  }

  if (elPayment) {
    elPayment.textContent = paymentStatus.toUpperCase();
    elPayment.style.color = isPaidOrWaived ? '#059669' : '#dc2626';
  }

  if (elInvoice) elInvoice.textContent = invoiceNumber;
  if (elStatusBadge) elStatusBadge.textContent = `STATUS: ${statusLabel}`;
  if (elStatusDot) {
    elStatusDot.style.background = isPaidOrWaived ? '#059669' : '#d97706';
  }

  if (elIssueDate) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    elIssueDate.textContent = new Date().toLocaleDateString('en-US', options);
  }

  modal.classList.add('active');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  document.documentElement.style.overflow = 'hidden';
}

function closeReceiptModal() {
  const modal = document.getElementById('consultation-receipt-modal');
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  }
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
}

function printReceiptDirectly() {
  const receiptEl = document.getElementById('consultation-printable-receipt');
  if (!receiptEl) {
    window.print();
    return;
  }

  const printWindow = window.open('', '_blank', 'width=850,height=950');
  if (!printWindow) {
    window.print();
    return;
  }

  const receiptHtml = receiptEl.outerHTML;
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Official Consultation Statement — Sabin Balan Finance</title>
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
      <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #ffffff; color: #1e293b; margin: 0; padding: 25px; box-sizing: border-box; }
        .receipt-paper { max-width: 780px; margin: 0 auto; padding: 30px; border: 1.5px solid #cbd5e1; border-radius: 14px; background: #ffffff; box-sizing: border-box; }
        .receipt-header { display: flex; justify-content: space-between; border-bottom: 2px solid #0f172a; padding-bottom: 18px; margin-bottom: 22px; gap: 15px; }
        .receipt-brand-block { display: flex; align-items: center; gap: 15px; }
        .receipt-firm-logo { width: 48px; height: auto; }
        .receipt-firm-title { margin: 0; font-size: 22px; color: #0f172a; font-weight: 800; letter-spacing: 1px; }
        .receipt-firm-subtitle { font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600; margin-top: 2px; }
        .receipt-doc-meta { text-align: right; }
        .receipt-meta-pill { background: #0f172a; color: #d4af37; padding: 4px 12px; font-size: 11px; font-weight: 700; border-radius: 4px; display: inline-block; }
        .receipt-ref-code-val { font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: 2px; margin: 5px 0; }
        .receipt-issue-date { font-size: 11px; color: #64748b; }
        .receipt-status-banner { display: flex; justify-content: space-between; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 18px; border-radius: 8px; margin-bottom: 22px; font-size: 13px; font-weight: 700; }
        .receipt-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 22px; }
        .receipt-info-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
        .receipt-card-header { font-size: 13px; font-weight: 800; color: #0f172a; border-bottom: 1px solid #cbd5e1; padding-bottom: 8px; margin-bottom: 12px; }
        .receipt-info-row { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px; gap: 8px; }
        .receipt-info-label { color: #64748b; }
        .receipt-info-value { font-weight: 600; color: #0f172a; text-align: right; word-break: break-word; }
        .receipt-mandate-card { background: #fffdf5; border: 1px solid #fef08a; border-radius: 8px; padding: 16px; margin-bottom: 22px; }
        .receipt-mandate-name { font-size: 15px; font-weight: 800; color: #854d0e; margin: 5px 0; }
        .receipt-mandate-desc { font-size: 12px; color: #713f12; margin: 0; line-height: 1.5; }
        .receipt-table { width: 100%; border-collapse: collapse; margin-bottom: 22px; font-size: 12px; }
        .receipt-table th { background: #0f172a; color: #ffffff; padding: 10px 14px; text-align: left; font-weight: 700; }
        .receipt-table td { padding: 12px 14px; border-bottom: 1px solid #e2e8f0; }
        .receipt-payment-meta { display: flex; justify-content: space-between; font-size: 12px; color: #64748b; margin-top: 10px; flex-wrap: wrap; gap: 6px; }
        .receipt-instructions-box { background: #f1f5f9; border-radius: 8px; padding: 14px 18px; margin-bottom: 22px; font-size: 12px; }
        .instructions-title { font-weight: 700; color: #0f172a; margin-bottom: 6px; }
        .instructions-list { margin: 0; padding-left: 20px; color: #475569; line-height: 1.6; }
        .receipt-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; padding-top: 18px; margin-top: 22px; gap: 15px; }
        .receipt-seal-block { display: flex; align-items: center; gap: 12px; }
        .fiduciary-seal-emblem { font-size: 26px; color: #059669; }
        .receipt-signature-block { text-align: right; }
        .signature-line { font-family: 'Playfair Display', Georgia, serif; font-size: 20px; font-style: italic; color: #0f172a; border-bottom: 1px solid #0f172a; display: inline-block; padding-bottom: 3px; }
        .signature-title { font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; margin-top: 5px; }
        @media (max-width: 640px) {
          body { padding: 12px; }
          .receipt-paper { padding: 16px; border-radius: 8px; }
          .receipt-header { flex-direction: column; align-items: flex-start; gap: 12px; }
          .receipt-doc-meta { text-align: left; }
          .receipt-status-banner { flex-direction: column; gap: 8px; align-items: flex-start; }
          .receipt-info-grid { grid-template-columns: 1fr; gap: 12px; }
          .receipt-table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
          .receipt-footer { flex-direction: column; align-items: flex-start; gap: 14px; }
          .receipt-signature-block { text-align: left; }
        }
        @media print {
          body { padding: 0; }
          .receipt-paper { border: none; padding: 0; max-width: 100%; }
        }
      </style>
    </head>
    <body>
      ${receiptHtml}
      <script>
        window.onload = function() {
          setTimeout(function() {
            window.print();
            window.close();
          }, 350);
        };
      </script>
    </body>
    </html>
  `);
  printWindow.document.close();
}


function copyReceiptDetails() {
  const refKey = document.getElementById('rcpt-ref-key')?.textContent.trim() || 'GT7K4M9P2X';
  const clientName = document.getElementById('rcpt-client-name')?.textContent.trim() || 'Client';
  const service = document.getElementById('rcpt-service-name')?.textContent.trim() || 'Advisory Consultation';
  const datetime = document.getElementById('rcpt-datetime')?.textContent.trim() || '';
  const duration = document.getElementById('rcpt-duration')?.textContent.trim() || '45 Minutes';
  const channel = document.getElementById('rcpt-channel')?.textContent.trim() || 'Encrypted Video';
  const fee = document.getElementById('rcpt-grand-total')?.textContent.trim() || '₹5,000.00 INR';
  const payment = document.getElementById('rcpt-payment-status')?.textContent.trim() || 'UNPAID';
  const invoice = document.getElementById('rcpt-invoice-id')?.textContent.trim() || 'INV-2026';

  const summaryText = `SABIN BALAN FINANCE — CONSULTATION CONFIRMATION & BILLING RECEIPT
======================================================================
Booking Reference: #${refKey}
Invoice / Tax Ref: ${invoice}
Client Name:       ${clientName}
Advisory Mandate:  ${service}
Schedule Date:     ${datetime}
Duration:          ${duration}
Meeting Channel:   ${channel}
Advisory Fee:      ${fee}
Payment Status:    ${payment}
Fiduciary Entity:  Sabin Balan Finance Advisory Group (#SB-70492)
======================================================================`;

  const btnLabel = document.getElementById('copy-receipt-btn-label');
  navigator.clipboard.writeText(summaryText).then(() => {
    if (btnLabel) btnLabel.textContent = 'Copied!';
    setTimeout(() => {
      if (btnLabel) btnLabel.textContent = 'Copy Summary';
    }, 2500);
  });
}

// Close modals on ESC key
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    closeReceiptModal();
    closeValidationModal();
  }
});
