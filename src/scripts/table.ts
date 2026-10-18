// Paged, filterable, sortable tables for the prototype data pages (F4, F20, F21).
// The pure functions are unit-tested in tests/table.spec.ts; mountTable wires them to the page.
import { escapeHtml } from './data';

type Value = string | number | null | undefined;
export type Getter<T> = (row: T) => Value;
export type Dir = 'asc' | 'desc';

const UNKNOWN = 'unknown';
const asText = (v: Value) => (v === null || v === undefined || v === '' ? UNKNOWN : String(v));

/** Keep rows that match every chosen facet value (exact) and contain the search text in one of `searchIn`. */
export function filterRows<T>(rows: T[], facets: Record<string, Getter<T>>, chosen: Record<string, string>,
  query: string, searchIn: Getter<T>[]): T[] {
  const active = Object.entries(chosen).filter(([k, v]) => v && facets[k]);
  const needle = query.trim().toLowerCase();
  return rows.filter((r) =>
    active.every(([k, v]) => asText(facets[k](r)) === v) &&
    (!needle || searchIn.some((get) => String(get(r) ?? '').toLowerCase().includes(needle))));
}

/** Stable sort; missing values always go last; text compares case-insensitively. Returns a new array. */
export function sortRows<T>(rows: T[], get: Getter<T>, dir: Dir): T[] {
  const sign = dir === 'asc' ? 1 : -1;
  return rows.map((r, i) => ({ r, i, v: get(r) })).sort((a, b) => {
    const am = a.v === null || a.v === undefined, bm = b.v === null || b.v === undefined;
    if (am || bm) return am === bm ? a.i - b.i : am ? 1 : -1;
    const c = typeof a.v === 'number' && typeof b.v === 'number' ? a.v - b.v
      : String(a.v).localeCompare(String(b.v), 'en', { sensitivity: 'base' });
    return c ? sign * c : a.i - b.i;
  }).map((x) => x.r);
}

export function pageOf<T>(rows: T[], page: number, size: number) {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const p = Math.min(Math.max(1, page), pages);
  return { rows: rows.slice((p - 1) * size, p * size), page: p, pages };
}

/** Distinct values with counts, most common first, ties alphabetical. */
export function facetCounts<T>(rows: T[], get: Getter<T>): [string, number][] {
  const m = new Map<string, number>();
  for (const r of rows) { const k = asText(get(r)); m.set(k, (m.get(k) ?? 0) + 1); }
  return [...m].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'en', { sensitivity: 'base' }));
}

export interface Column<T> { label: string; cell: (row: T) => string; sort?: Getter<T>; num?: boolean }
export interface TableOptions<T> {
  rows: T[]; columns: Column<T>[]; caption: string; label: string;
  facets: { key: string; label: string; get: Getter<T>; show?: (v: string) => string }[];
  search?: { label: string; in: Getter<T>[] };
  sort?: { column: number; dir: Dir };
  noun: string;
  /** Called after every render with all rows that match the filters, in table order (to redraw a linked plot). */
  onView?: (rows: T[], selected: T | null) => void;
  /** Detail panel: HTML for the selected row. Without it the table has no selectable rows. */
  detail?: (row: T) => string;
  onSelect?: (row: T | null) => void;
}

export interface TableHandle<T> { select: (row: T | null) => void }

const SIZES = [25, 50, 100];

/** Render filters, a sortable table and a pager into `root`. Escapes nothing in `cell` output: cells must escape. */
export function mountTable<T>(root: HTMLElement, o: TableOptions<T>): TableHandle<T> {
  const chosen: Record<string, string> = {};
  let query = '', sort = o.sort ?? null, page = 1, size = SIZES[0];
  let selected: T | null = null, view: T[] = [];
  const getters = Object.fromEntries(o.facets.map((f) => [f.key, f.get]));

  const selects = o.facets.map((f) => {
    const opts = facetCounts(o.rows, f.get).map(([v, n]) =>
      `<option value="${escapeHtml(v)}">${escapeHtml(f.show ? f.show(v) : v)} (${n.toLocaleString('en')})</option>`).join('');
    return `<label>${escapeHtml(f.label)}<select data-facet="${f.key}" aria-label="${escapeHtml(f.label)}"><option value="">All</option>${opts}</select></label>`;
  }).join('');
  const search = o.search ? `<label>${escapeHtml(o.search.label)}<input type="search" data-search aria-label="${escapeHtml(o.search.label)}" /></label>` : '';
  root.innerHTML = `<div class="workspace${o.detail ? ' has-detail' : ''}">
    <div class="side" role="group" aria-label="Filters"><div class="filters">${search}${selects}
      <label>Rows per page<select data-size aria-label="Rows per page">${SIZES.map((s) => `<option>${s}</option>`).join('')}</select></label>
      <button type="button" data-reset>Clear filters</button></div></div>
    <div class="main-pane">
    <p class="caption" aria-live="polite" data-count></p>
    <div class="table-box" tabindex="0" role="region" aria-label="${escapeHtml(o.label)}"><table>
      <caption>${o.caption}</caption>
      <thead><tr>${o.columns.map((c, i) => `<th scope="col"${c.num ? ' class="num"' : ''} data-col="${i}">${c.sort
        ? `<button type="button" class="sort" data-sort="${i}">${escapeHtml(c.label)}<span aria-hidden="true"></span></button>`
        : escapeHtml(c.label)}</th>`).join('')}</tr></thead>
      <tbody></tbody></table></div>
    <nav class="pager" aria-label="${escapeHtml(o.label)} pages">
      <button type="button" data-page="-1">Previous</button><span data-pos></span><button type="button" data-page="1">Next</button></nav></div>
    ${o.detail ? '<div class="detail" role="group" aria-label="Selected row" aria-live="polite" data-detail></div>' : ''}</div>`;

  const $ = <E extends Element>(sel: string) => root.querySelector<E>(sel)!;
  const render = () => {
    let hits = filterRows(o.rows, getters, chosen, query, o.search?.in ?? []);
    if (sort && o.columns[sort.column].sort) hits = sortRows(hits, o.columns[sort.column].sort!, sort.dir);
    view = hits;
    const p = pageOf(hits, page, size);
    page = p.page;
    $('tbody').innerHTML = p.rows.map((r, n) => `<tr${o.detail ? ` tabindex="0" data-i="${(p.page - 1) * size + n}"` : ''}${r === selected ? ' aria-current="true"' : ''}>${o.columns.map((c) =>
      `<td${c.num ? ' class="num"' : ''}>${c.cell(r)}</td>`).join('')}</tr>`).join('');
    $('[data-count]').textContent = `${hits.length.toLocaleString('en')} of ${o.rows.length.toLocaleString('en')} ${o.noun} match.`;
    $('[data-pos]').textContent = `Page ${p.page} of ${p.pages}`;
    $<HTMLButtonElement>('[data-page="-1"]').disabled = p.page <= 1;
    $<HTMLButtonElement>('[data-page="1"]').disabled = p.page >= p.pages;
    root.querySelectorAll<HTMLElement>('th[data-col]').forEach((th) => {
      const on = sort && Number(th.dataset.col) === sort.column;
      if (on) th.setAttribute('aria-sort', sort!.dir === 'asc' ? 'ascending' : 'descending'); else th.removeAttribute('aria-sort');
      const mark = th.querySelector('span');
      if (mark) mark.textContent = on ? (sort!.dir === 'asc' ? ' ▲' : ' ▼') : '';
    });
    if (o.detail) {
      $('[data-detail]').innerHTML = selected ? o.detail(selected) : '<p class="caption">Select a row (click it, or use the arrow keys) to see its details here.</p>';
    }
    o.onView?.(hits, selected);
  };
  const choose = (row: T | null, focus = false) => {
    selected = row;
    const i = row ? view.indexOf(row) : -1;
    if (i >= 0) page = Math.floor(i / size) + 1;
    o.onSelect?.(row);
    render();
    const tr = i >= 0 ? root.querySelector<HTMLElement>('tr[aria-current="true"]') : null;
    if (focus) tr?.focus(); // the table body was redrawn, so keyboard users would otherwise lose their place
    tr?.scrollIntoView({ block: 'nearest' });
  };

  root.addEventListener('change', (e) => {
    const el = e.target as HTMLSelectElement;
    if (el.dataset.facet) chosen[el.dataset.facet] = el.value;
    if (el.hasAttribute('data-size')) size = Number(el.value);
    page = 1; render();
  });
  root.addEventListener('input', (e) => {
    const el = e.target as HTMLInputElement;
    if (el.hasAttribute('data-search')) { query = el.value; page = 1; render(); }
  });
  const rowOf = (el: HTMLElement) => { const tr = el.closest<HTMLElement>('tr[data-i]'); return tr ? view[Number(tr.dataset.i)] : undefined; };
  root.addEventListener('keydown', (e) => {
    const tr = (e.target as HTMLElement).closest<HTMLElement>('tr[data-i]');
    if (!tr) return;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(rowOf(tr)!, true); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const next = e.key === 'ArrowDown' ? tr.nextElementSibling : tr.previousElementSibling;
      if (next) { e.preventDefault(); choose(rowOf(next as HTMLElement)!, true); }
    }
  });
  document.addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement;
    if (e.key === '/' && !e.ctrlKey && !e.metaKey && !/^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName)) {
      const s = root.querySelector<HTMLInputElement>('[data-search]');
      if (s) { e.preventDefault(); s.focus(); }
    }
  });
  root.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const row = o.detail && !target.closest('a, button') ? rowOf(target) : undefined;
    if (row) { choose(row === selected ? null : row, true); return; }
    const b = target.closest('button');
    if (!b) return;
    if (b.dataset.sort) {
      const col = Number(b.dataset.sort);
      sort = { column: col, dir: sort?.column === col && sort.dir === 'asc' ? 'desc' : 'asc' };
      page = 1;
    } else if (b.dataset.page) page += Number(b.dataset.page);
    else if (b.hasAttribute('data-reset')) {
      for (const k of Object.keys(chosen)) delete chosen[k];
      query = ''; page = 1;
      root.querySelectorAll<HTMLSelectElement>('select[data-facet]').forEach((s) => { s.value = ''; });
      const s = root.querySelector<HTMLInputElement>('[data-search]'); if (s) s.value = '';
    }
    render();
  });
  render();
  return { select: choose };
}
