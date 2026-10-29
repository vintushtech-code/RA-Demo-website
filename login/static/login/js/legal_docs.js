/**
 * GuardianTree FP — Legal Documentation Scripts
 * Handles Document Printing, Copy Link with toast fallback, and Scrollspy for Table of Contents.
 */

// 1. Print & Speech Assist Functionality
function printLegalDocument() {
  window.print();
}

function speakLegalDocumentText() {
  const docBody = document.getElementById('document-body-content');
  if (!docBody) return;
  
  if (typeof enableSpeechMode === 'function') {
    enableSpeechMode();
  }
  
  const textToRead = docBody.innerText || docBody.textContent || '';
  if (typeof speakText === 'function') {
    speakText("Now reading document: " + textToRead.substring(0, 800) + "...", true);
    if (typeof showToast === 'function') {
      showToast('Audio speech narration started for this document.', 'info');
    }
  }
}

// 2. Share / Copy Link Functionality
function copyDocumentLink() {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(window.location.href).then(function() {
      if (typeof showToast === 'function') {
        showToast('Document link copied to clipboard successfully!', 'success');
      } else {
        alert('Document link copied to clipboard!');
      }
    }).catch(function() {
      fallbackCopyLink();
    });
  } else {
    fallbackCopyLink();
  }
}

function fallbackCopyLink() {
  const dummy = document.createElement('input');
  document.body.appendChild(dummy);
  dummy.value = window.location.href;
  dummy.select();
  document.execCommand('copy');
  document.body.removeChild(dummy);
  if (typeof showToast === 'function') {
    showToast('Document link copied to clipboard!', 'success');
  } else {
    alert('Document link copied to clipboard!');
  }
}

// 3. Scrollspy for Active Table of Contents Link
document.addEventListener('DOMContentLoaded', function() {
  const sections = document.querySelectorAll('.doc-section-block');
  const tocLinks = document.querySelectorAll('.clean-toc-link');

  if (sections.length > 0 && tocLinks.length > 0) {
    window.addEventListener('scroll', function() {
      let currentSectionId = '';
      const scrollPosition = window.scrollY + 140;

      sections.forEach(function(section) {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.offsetHeight;
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
          currentSectionId = section.getAttribute('id');
        }
      });

      tocLinks.forEach(function(link) {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + currentSectionId) {
          link.classList.add('active');
        }
      });
    });
  }
});
