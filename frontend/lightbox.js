/* ============================================================
   Memoria — Lightbox Component
   Simple photo lightbox with keyboard navigation.
   Vanilla JS, no dependencies.
   ============================================================ */

var Lightbox = (function () {
  'use strict';

  var _overlay = null;
  var _photos = [];
  var _index = 0;

  // ==================== PUBLIC API ====================

  /**
   * Open the lightbox at a specific photo.
   * @param {Array} photos - Array of photo objects with url, caption, by, time
   * @param {number} startIndex - Index to start at
   */
  function open(photos, startIndex) {
    if (!photos || photos.length === 0) return;

    _photos = photos;
    _index = startIndex || 0;

    createOverlay();
    updateContent();

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Animate in
    requestAnimationFrame(function () {
      _overlay.classList.add('visible');
    });

    // Bind keyboard
    document.addEventListener('keydown', onKeyDown);
  }

  /**
   * Close the lightbox.
   */
  function close() {
    if (!_overlay) return;

    _overlay.classList.remove('visible');
    document.body.style.overflow = '';
    document.removeEventListener('keydown', onKeyDown);

    // Remove after transition
    setTimeout(function () {
      if (_overlay && _overlay.parentNode) {
        _overlay.parentNode.removeChild(_overlay);
      }
      _overlay = null;
    }, 300);
  }

  // ==================== INTERNALS ====================

  function createOverlay() {
    // Remove existing if any
    if (_overlay && _overlay.parentNode) {
      _overlay.parentNode.removeChild(_overlay);
    }

    _overlay = document.createElement('div');
    _overlay.className = 'lightbox-overlay';

    // Close on click outside image
    _overlay.addEventListener('click', function (e) {
      if (e.target === _overlay) close();
    });

    // Content wrapper
    var content = document.createElement('div');
    content.className = 'lightbox-content';

    // Close button
    var closeBtn = document.createElement('button');
    closeBtn.className = 'lightbox-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.setAttribute('aria-label', 'Close lightbox');
    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      close();
    });
    content.appendChild(closeBtn);

    // Image
    var img = document.createElement('img');
    img.className = 'lightbox-img';
    img.alt = '';
    content.appendChild(img);

    // Caption
    var caption = document.createElement('div');
    caption.className = 'lightbox-caption';
    content.appendChild(caption);

    // Meta (by / time)
    var meta = document.createElement('div');
    meta.className = 'lightbox-meta';
    content.appendChild(meta);

    // Counter
    var counter = document.createElement('div');
    counter.className = 'lightbox-counter';
    content.appendChild(counter);

    // Nav buttons (only if multiple photos)
    if (_photos.length > 1) {
      var prevBtn = document.createElement('button');
      prevBtn.className = 'lightbox-nav lightbox-prev';
      prevBtn.innerHTML = '&#8249;';
      prevBtn.setAttribute('aria-label', 'Previous photo');
      prevBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        navigate(-1);
      });
      content.appendChild(prevBtn);

      var nextBtn = document.createElement('button');
      nextBtn.className = 'lightbox-nav lightbox-next';
      nextBtn.innerHTML = '&#8250;';
      nextBtn.setAttribute('aria-label', 'Next photo');
      nextBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        navigate(1);
      });
      content.appendChild(nextBtn);
    }

    _overlay.appendChild(content);
    document.body.appendChild(_overlay);
  }

  function updateContent() {
    if (!_overlay) return;

    var photo = _photos[_index];
    var img = _overlay.querySelector('.lightbox-img');
    var caption = _overlay.querySelector('.lightbox-caption');
    var meta = _overlay.querySelector('.lightbox-meta');
    var counter = _overlay.querySelector('.lightbox-counter');

    img.src = photo.url;
    img.alt = photo.alt || photo.caption || '';

    caption.textContent = photo.caption || '';
    caption.style.display = photo.caption ? '' : 'none';

    // Build meta line: "by Name at Time"
    var metaParts = [];
    if (photo.by) metaParts.push('by ' + photo.by);
    if (photo.time) metaParts.push('at ' + photo.time);
    meta.textContent = metaParts.join(' ');
    meta.style.display = metaParts.length > 0 ? '' : 'none';

    counter.textContent = (_index + 1) + ' / ' + _photos.length;
    counter.style.display = _photos.length > 1 ? '' : 'none';
  }

  function navigate(direction) {
    _index = (_index + direction + _photos.length) % _photos.length;
    updateContent();
  }

  function onKeyDown(e) {
    switch (e.key) {
      case 'Escape':
        close();
        break;
      case 'ArrowLeft':
        navigate(-1);
        break;
      case 'ArrowRight':
        navigate(1);
        break;
    }
  }

  // ==================== PUBLIC INTERFACE ====================

  return {
    open: open,
    close: close
  };
})();
