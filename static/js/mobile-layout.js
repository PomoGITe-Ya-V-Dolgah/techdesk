(() => {
  'use strict';
  const mobile = matchMedia('(max-width: 992px)');
  const panels = [...document.querySelectorAll('[data-mobile-filters]')];
  const update = () => panels.forEach(panel => {
    panel.open = !mobile.matches || panel.dataset.hasFilters === 'true';
  });
  update();
  mobile.addEventListener('change', update);
})();
