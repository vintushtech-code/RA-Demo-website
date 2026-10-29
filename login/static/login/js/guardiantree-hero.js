/**
 * GuardianTree FP — Rolling Hero Carousel Engine
 * Autoplay with pause on hover/focus, smooth transitions, dot indicators,
 * arrow keys, touch swipe, and accessibility live announcements.
 */
document.addEventListener('DOMContentLoaded', function () {
  var hero = document.querySelector('.gt-hero');
  if (!hero) return;
  var frames = hero.querySelectorAll('.gt-frame');
  var themes = ['welcome', 'fiduciary', 'personal', 'pace', 'compound', 'framework'];
  var dotsWrap = hero.querySelector('.gt-dots');
  var live = hero.querySelector('.gt-sr');
  var INTERVAL = 6500;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var i = 0, timer = null, paused = false;

  if (dotsWrap && frames.length > 0) {
    dotsWrap.innerHTML = '';
    frames.forEach(function (_, n) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'gt-dot';
      b.setAttribute('aria-label', 'Go to slide ' + (n + 1));
      b.addEventListener('click', function () { go(n, true); });
      dotsWrap.appendChild(b);
    });
  }
  var dots = dotsWrap ? dotsWrap.querySelectorAll('.gt-dot') : [];

  function go(n, user) {
    if (!frames.length) return;
    i = (n + frames.length) % frames.length;
    frames.forEach(function (f, k) {
      f.classList.toggle('is-active', k === i);
      f.setAttribute('aria-hidden', k === i ? 'false' : 'true');
    });
    dots.forEach(function (d, k) {
      d.setAttribute('aria-current', k === i ? 'true' : 'false');
    });
    if (themes[i]) {
      hero.setAttribute('data-theme', themes[i]);
    }
    if (user && live) {
      live.textContent = 'Slide ' + (i + 1) + ' of ' + frames.length;
      restart();
    }
  }

  function start() {
    if (!reduce && !paused && !timer) {
      timer = setInterval(function () { go(i + 1); }, INTERVAL);
    }
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function restart() {
    stop();
    start();
  }

  var prevBtn = hero.querySelector('.gt-prev');
  var nextBtn = hero.querySelector('.gt-next');
  if (prevBtn) prevBtn.addEventListener('click', function () { go(i - 1, true); });
  if (nextBtn) nextBtn.addEventListener('click', function () { go(i + 1, true); });

  hero.addEventListener('mouseenter', function () { paused = true; stop(); });
  hero.addEventListener('mouseleave', function () { paused = false; start(); });
  hero.addEventListener('focusin', function () { paused = true; stop(); });
  hero.addEventListener('focusout', function () { paused = false; start(); });
  document.addEventListener('visibilitychange', function () { document.hidden ? stop() : start(); });

  hero.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') go(i - 1, true);
    if (e.key === 'ArrowRight') go(i + 1, true);
  });

  var x0 = null;
  hero.addEventListener('touchstart', function (e) {
    if (e.touches && e.touches[0]) {
      x0 = e.touches[0].clientX;
    }
  }, { passive: true });

  hero.addEventListener('touchend', function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 40) go(i + (dx < 0 ? 1 : -1), true);
  });

  go(0);
  start();
});
