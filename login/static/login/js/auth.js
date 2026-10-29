/**
 * GuardianTree FP — Authentication Scripts
 * Handles Password visibility toggle and 6-digit OTP verification inputs.
 */

function togglePasswordVisibility(fieldId, btn) {
  const input = document.getElementById(fieldId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "Hide";
  } else {
    input.type = "password";
    btn.textContent = "Show";
  }
}

document.addEventListener('DOMContentLoaded', function() {
  const digit1 = document.getElementById('digit1');
  if (!digit1) return; // Not an OTP verification page

  const boxes = [
    document.getElementById('digit1'),
    document.getElementById('digit2'),
    document.getElementById('digit3'),
    document.getElementById('digit4'),
    document.getElementById('digit5'),
    document.getElementById('digit6')
  ];
  const hiddenInput = document.getElementById('otp_code_hidden');
  const form = document.getElementById('otp-form');

  if (boxes[0]) boxes[0].focus();

  function updateHiddenCode() {
    if (!hiddenInput) return;
    const code = boxes.map(b => b ? b.value : '').join('');
    hiddenInput.value = code;
  }

  boxes.forEach((box, idx) => {
    if (!box) return;

    box.addEventListener('input', function() {
      this.value = this.value.replace(/[^0-9]/g, '');
      if (this.value && idx < 5 && boxes[idx + 1]) {
        boxes[idx + 1].focus();
      }
      updateHiddenCode();

      if (hiddenInput && hiddenInput.value.length === 6 && form) {
        form.submit();
      }
    });

    box.addEventListener('keydown', function(e) {
      if (e.key === 'Backspace') {
        if (!this.value && idx > 0 && boxes[idx - 1]) {
          boxes[idx - 1].focus();
          boxes[idx - 1].value = '';
          updateHiddenCode();
        }
      }
    });

    box.addEventListener('paste', function(e) {
      e.preventDefault();
      const pasteData = (e.clipboardData || window.clipboardData).getData('text').trim().replace(/[^0-9]/g, '');
      if (pasteData.length >= 6) {
        for (let i = 0; i < 6; i++) {
          if (boxes[i]) boxes[i].value = pasteData[i];
        }
        if (boxes[5]) boxes[5].focus();
        updateHiddenCode();
        if (form) form.submit();
      } else if (pasteData.length > 0) {
        for (let i = 0; i < pasteData.length && (idx + i) < 6; i++) {
          if (boxes[idx + i]) boxes[idx + i].value = pasteData[i];
        }
        const nextIdx = Math.min(5, idx + pasteData.length);
        if (boxes[nextIdx]) boxes[nextIdx].focus();
        updateHiddenCode();
      }
    });
  });

  // Countdown Timer
  const timerElem = document.getElementById('countdown-timer');
  if (timerElem) {
    const rawSecs = timerElem.getAttribute('data-seconds');
    let totalSeconds = rawSecs ? parseInt(rawSecs) : 300;

    function updateTimer() {
      if (totalSeconds <= 0) {
        timerElem.textContent = "00:00 (Expired)";
        timerElem.style.color = "#FF4D4D";
        return;
      }
      const mins = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      timerElem.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
      totalSeconds--;
    }

    updateTimer();
    setInterval(updateTimer, 1000);
  }
});
