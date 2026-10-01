(() => {
  'use strict';
  const collator = new Intl.Collator('ru', {numeric: true, sensitivity: 'base'});
  document.querySelectorAll('table[data-sort-table]').forEach(table => {
    const body = table.tBodies[0];
    const headers = [...table.querySelectorAll('thead th')];
    if (!body || !headers.length) return;
    const parameter = `sort_${table.dataset.sortTable}`;
    let active = -1, descending = false;
    const buttons = [];
    function sort(index, reverse, updateUrl) {
      active = index; descending = reverse;
      const rows = [...body.rows].filter(row => row.cells.length === headers.length && !row.cells[0].hasAttribute('colspan'));
      function value(row) {
        const cell = row.cells[index];
        const raw = (cell.dataset.sortValue ?? cell.textContent).trim();
        if (!raw || raw === '—' || raw === 'не назначен') return null;
        if (headers[index].dataset.sortType === 'number') {
          const number = Number(raw.replace(/^#/, '').replace(/\s/g, '').replace(',', '.'));
          return Number.isFinite(number) ? number : null;
        }
        if (headers[index].dataset.sortType === 'date') {
          const number = Date.parse(raw);
          return Number.isFinite(number) ? number : null;
        }
        return raw;
      }
      rows.map((row, position) => ({row, position, value: value(row)})).sort((a, b) => {
        if (a.value === null || b.value === null) return a.value === b.value ? a.position - b.position : a.value === null ? 1 : -1;
        const order = typeof a.value === 'number' ? a.value - b.value : collator.compare(a.value, b.value);
        return (reverse ? -order : order) || a.position - b.position;
      }).forEach(({row}) => body.append(row));
      headers.forEach((header, column) => {
        if (!buttons[column]) return;
        if (column === index) header.setAttribute('aria-sort', reverse ? 'descending' : 'ascending');
        else header.removeAttribute('aria-sort');
        const nextDescending = column === index && !reverse;
        buttons[column].textContent = `${buttons[column].dataset.label}${column === index ? reverse ? ' ↓' : ' ↑' : ''}`;
        buttons[column].setAttribute('aria-label', `${buttons[column].dataset.label}: сортировать ${nextDescending ? 'по убыванию' : 'по возрастанию'}`);
      });
      if (updateUrl) {
        const url = new URL(location.href);
        url.searchParams.set(parameter, `${index}:${reverse ? 'desc' : 'asc'}`);
        history.replaceState(null, '', url);
      }
    }
    headers.forEach((header, index) => {
      if (header.hasAttribute('data-sort-disabled')) return;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'table-sort-button';
      button.dataset.label = header.textContent.trim(); button.textContent = button.dataset.label;
      button.setAttribute('aria-label', `${button.dataset.label}: сортировать по возрастанию`);
      button.addEventListener('click', () => sort(index, active === index ? !descending : false, true));
      header.replaceChildren(button); buttons[index] = button;
    });
    const saved = new URL(location.href).searchParams.get(parameter);
    if (saved && /^\d+:(asc|desc)$/.test(saved)) {
      const [index, direction] = saved.split(':');
      if (buttons[Number(index)]) sort(Number(index), direction === 'desc', false);
    }
  });
})();
