/* ============================================================
   Memoria — Memories Component (Journal + Scrapbook)
   Vanilla JS, no framework, no build step.
   Loads manifest.json, determines trip phase, renders views.
   ============================================================ */

var Memories = (function () {
  'use strict';

  var _container = null;
  var _manifest = null;
  var _view = 'journal'; // 'journal' | 'scrapbook'
  var _scrapbookFilter = { type: 'all', value: null }; // { type: 'all'|'day'|'person', value }

  // ==================== PUBLIC API ====================

  function init(containerId, manifestUrl) {
    _container = document.getElementById(containerId);
    if (!_container) {
      console.error('[Memories] Container not found: #' + containerId);
      return;
    }

    _container.innerHTML = '<div class="memories-loading">Loading memories...</div>';

    fetch(manifestUrl)
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to load manifest: ' + res.status);
        return res.json();
      })
      .then(function (manifest) {
        _manifest = manifest;
        var phase = detectPhase(manifest.trip);
        if (phase === 'pre') {
          _container.innerHTML = '';
          return; // nothing to show yet
        }
        render(phase);
      })
      .catch(function (err) {
        console.error('[Memories]', err);
        _container.innerHTML = '<div class="memories-empty">Could not load memories.</div>';
      });
  }

  // ==================== PHASE DETECTION ====================

  function detectPhase(trip) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);

    var start = parseDate(trip.dates.start);
    var end = parseDate(trip.dates.end);

    if (today < start) return 'pre';
    if (today > end) return 'post';
    return 'during';
  }

  function parseDate(str) {
    // "2026-05-21" -> local midnight Date
    var parts = str.split('-');
    return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
  }

  // ==================== RENDERING ====================

  function render(phase) {
    var days = getVisibleDays(phase);
    if (days.length === 0) {
      _container.innerHTML = '<div class="memories-empty">No memories yet — check back soon!</div>';
      return;
    }

    _container.innerHTML = '';

    // Nav toggle
    var nav = el('div', 'memories-nav');
    var btnJournal = el('button', _view === 'journal' ? 'active' : '', 'Journal');
    var btnScrapbook = el('button', _view === 'scrapbook' ? 'active' : '', 'Scrapbook');

    btnJournal.addEventListener('click', function () {
      _view = 'journal';
      render(phase);
    });
    btnScrapbook.addEventListener('click', function () {
      _view = 'scrapbook';
      render(phase);
    });

    nav.appendChild(btnJournal);
    nav.appendChild(btnScrapbook);
    _container.appendChild(nav);

    // View content
    var content = el('div', 'memories-content');
    if (_view === 'journal') {
      renderJournal(content, days);
    } else {
      renderScrapbook(content, days);
    }
    _container.appendChild(content);
  }

  function getVisibleDays(phase) {
    if (!_manifest || !_manifest.days) return [];
    if (phase === 'post') return _manifest.days;

    // During trip: only show days whose date has passed
    var today = new Date();
    today.setHours(23, 59, 59, 999);

    return _manifest.days.filter(function (day) {
      return parseDate(day.date) <= today;
    });
  }

  // ==================== JOURNAL VIEW ====================

  function renderJournal(container, days) {
    days.forEach(function (day) {
      var card = el('div', 'journal-day');

      // Day label
      var label = el('div', 'journal-day-label', day.label);
      card.appendChild(label);

      // Day title
      if (day.title) {
        var title = el('h3', 'journal-day-title', day.title);
        card.appendChild(title);
      }

      // Separate photos and quotes from journal entries
      var photos = [];
      var quotes = [];
      if (day.journal) {
        day.journal.forEach(function (entry) {
          if (entry.type === 'photo') photos.push(entry);
          else if (entry.type === 'quote') quotes.push(entry);
        });
      }

      // Hero photo (first photo or highest quality)
      if (photos.length > 0) {
        var heroPhoto = photos[0];
        var heroDiv = el('div', 'journal-hero');
        var heroImg = document.createElement('img');
        heroImg.src = heroPhoto.url;
        heroImg.alt = heroPhoto.alt || heroPhoto.caption || '';
        heroImg.loading = 'lazy';
        heroImg.addEventListener('click', function () {
          var allPhotos = photos.concat(day.scrapbook || []);
          Lightbox.open(allPhotos, 0);
        });
        heroDiv.appendChild(heroImg);
        card.appendChild(heroDiv);
      }

      // Supporting photos
      if (photos.length > 1) {
        var supporting = el('div', 'journal-supporting');
        var supportingPhotos = photos.slice(1, 4); // up to 3 supporting
        supportingPhotos.forEach(function (photo, idx) {
          var img = document.createElement('img');
          img.src = photo.thumb || photo.url;
          img.alt = photo.alt || photo.caption || '';
          img.loading = 'lazy';
          img.addEventListener('click', function () {
            var allPhotos = photos.concat(day.scrapbook || []);
            Lightbox.open(allPhotos, idx + 1);
          });
          supporting.appendChild(img);
        });
        card.appendChild(supporting);
      }

      // Day summary
      if (day.summary) {
        var summary = el('p', 'journal-summary', day.summary);
        card.appendChild(summary);
      }

      // Pull-quotes
      quotes.forEach(function (q) {
        var quoteDiv = el('div', 'journal-quote');
        var quoteText = el('p', '', '\u201C' + q.text + '\u201D');
        var quoteAttr = el('span', 'journal-quote-attribution', '\u2014 ' + q.by + (q.time ? ', ' + q.time : ''));
        quoteDiv.appendChild(quoteText);
        quoteDiv.appendChild(quoteAttr);
        card.appendChild(quoteDiv);
      });

      container.appendChild(card);
    });
  }

  // ==================== SCRAPBOOK VIEW ====================

  function renderScrapbook(container, days) {
    // Collect all scrapbook photos with day metadata
    var allPhotos = [];
    var dayLabels = [];
    var people = {};

    days.forEach(function (day) {
      var dayPhotos = (day.scrapbook || []).concat(
        (day.journal || []).filter(function (e) { return e.type === 'photo'; })
      );

      dayPhotos.forEach(function (photo) {
        allPhotos.push({
          url: photo.url,
          thumb: photo.thumb || photo.url,
          caption: photo.caption || '',
          alt: photo.alt || '',
          by: photo.by || '',
          time: photo.time || '',
          location: photo.location || '',
          category: photo.category || '',
          dayNumber: day.dayNumber,
          dayLabel: day.label
        });
        if (photo.by) people[photo.by] = true;
      });

      if (dayPhotos.length > 0) {
        dayLabels.push({ number: day.dayNumber, label: 'Day ' + day.dayNumber });
      }
    });

    if (allPhotos.length === 0) {
      container.appendChild(el('div', 'memories-empty', 'No photos yet.'));
      return;
    }

    // Filter chips
    var filters = el('div', 'scrapbook-filters');

    var btnAll = el('button', _scrapbookFilter.type === 'all' ? 'active' : '', 'All');
    btnAll.addEventListener('click', function () {
      _scrapbookFilter = { type: 'all', value: null };
      renderScrapbookGrid(grid, allPhotos);
      updateFilterButtons(filters);
    });
    filters.appendChild(btnAll);

    // Day filters
    dayLabels.forEach(function (d) {
      var btn = el('button', '', d.label);
      btn.dataset.filterType = 'day';
      btn.dataset.filterValue = d.number;
      btn.addEventListener('click', function () {
        _scrapbookFilter = { type: 'day', value: d.number };
        renderScrapbookGrid(grid, allPhotos);
        updateFilterButtons(filters);
      });
      filters.appendChild(btn);
    });

    // Person filters
    Object.keys(people).sort().forEach(function (name) {
      var btn = el('button', '', name);
      btn.dataset.filterType = 'person';
      btn.dataset.filterValue = name;
      btn.addEventListener('click', function () {
        _scrapbookFilter = { type: 'person', value: name };
        renderScrapbookGrid(grid, allPhotos);
        updateFilterButtons(filters);
      });
      filters.appendChild(btn);
    });

    container.appendChild(filters);
    updateFilterButtons(filters);

    // Photo grid
    var grid = el('div', 'scrapbook-grid');
    renderScrapbookGrid(grid, allPhotos);
    container.appendChild(grid);
  }

  function renderScrapbookGrid(grid, allPhotos) {
    grid.innerHTML = '';

    var filtered = allPhotos;
    if (_scrapbookFilter.type === 'day') {
      filtered = allPhotos.filter(function (p) { return p.dayNumber === _scrapbookFilter.value; });
    } else if (_scrapbookFilter.type === 'person') {
      filtered = allPhotos.filter(function (p) { return p.by === _scrapbookFilter.value; });
    }

    filtered.forEach(function (photo, idx) {
      var card = el('div', 'scrapbook-photo');

      var img = document.createElement('img');
      img.src = photo.thumb;
      img.alt = photo.alt || photo.caption || '';
      img.loading = 'lazy';

      card.addEventListener('click', function () {
        Lightbox.open(filtered, idx);
      });

      card.appendChild(img);

      if (photo.caption) {
        var caption = el('div', 'scrapbook-photo-caption', photo.caption);
        card.appendChild(caption);
      }

      var meta = [];
      if (photo.by) meta.push(photo.by);
      if (photo.time) meta.push(photo.time);
      if (meta.length > 0) {
        var metaDiv = el('div', 'scrapbook-photo-meta', meta.join(' \u00B7 '));
        card.appendChild(metaDiv);
      }

      grid.appendChild(card);
    });
  }

  function updateFilterButtons(filtersEl) {
    var buttons = filtersEl.querySelectorAll('button');
    buttons.forEach(function (btn) {
      var isActive = false;
      if (_scrapbookFilter.type === 'all' && !btn.dataset.filterType) {
        isActive = true;
      } else if (btn.dataset.filterType === _scrapbookFilter.type) {
        if (_scrapbookFilter.type === 'day') {
          isActive = parseInt(btn.dataset.filterValue, 10) === _scrapbookFilter.value;
        } else {
          isActive = btn.dataset.filterValue === _scrapbookFilter.value;
        }
      }
      btn.classList.toggle('active', isActive);
    });
  }

  // ==================== HELPERS ====================

  function el(tag, className, textContent) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (textContent) node.textContent = textContent;
    return node;
  }

  // ==================== PUBLIC INTERFACE ====================

  return {
    init: init
  };
})();
