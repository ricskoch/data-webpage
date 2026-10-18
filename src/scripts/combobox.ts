// Gene-symbol autocomplete (F20): a listbox under a text input, so a lookup can only start from a known symbol.
// `suggest` is pure and unit-tested in tests/combobox.spec.ts; `mountCombobox` wires it to an input.
import { escapeHtml } from './data';

/** Symbols that start with the query first, then those that merely contain it; case-insensitive, at most `limit`. */
export function suggest(symbols: string[], query: string, limit = 12): string[] {
  const q = query.trim().toUpperCase();
  if (!q) return [];
  const starts: string[] = [], inside: string[] = [];
  for (const s of symbols) {
    const u = s.toUpperCase();
    if (u.startsWith(q)) starts.push(s); else if (u.includes(q)) inside.push(s);
  }
  const byName = (a: string, b: string) => a.length - b.length || a.localeCompare(b, 'en', { sensitivity: 'base' });
  return [...starts.sort(byName), ...inside.sort(byName)].slice(0, limit);
}

/** The known symbol that equals `query` ignoring case, or undefined. */
export const exactSymbol = (symbols: string[], query: string) =>
  symbols.find((s) => s.toUpperCase() === query.trim().toUpperCase());

let counter = 0;

/** Attach a suggestion list to `input`. `symbols` is read on every keystroke, so it may load later. */
export function mountCombobox(input: HTMLInputElement, symbols: () => string[], onPick: (symbol: string) => void): void {
  const id = `combo-${++counter}`;
  const list = document.createElement('ul');
  list.id = id; list.className = 'suggestions'; list.setAttribute('role', 'listbox'); list.hidden = true;
  list.setAttribute('aria-label', 'Matching genes');
  input.after(list);
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-autocomplete', 'list');
  input.setAttribute('aria-controls', id);
  input.setAttribute('aria-expanded', 'false');
  let items: string[] = [], active = -1;

  const close = () => { list.hidden = true; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); active = -1; };
  const mark = () => {
    list.querySelectorAll('li').forEach((li, i) => li.setAttribute('aria-selected', String(i === active)));
    if (active >= 0) input.setAttribute('aria-activedescendant', `${id}-${active}`); else input.removeAttribute('aria-activedescendant');
  };
  const open = () => {
    items = suggest(symbols(), input.value);
    list.innerHTML = items.map((s, i) => `<li role="option" id="${id}-${i}" aria-selected="false" data-s="${escapeHtml(s)}"><span class="gene">${escapeHtml(s)}</span></li>`).join('');
    list.hidden = !items.length;
    input.setAttribute('aria-expanded', String(items.length > 0));
    active = -1;
  };
  const pick = (s: string) => { input.value = s; close(); onPick(s); };

  input.addEventListener('input', open);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (list.hidden) open();
      if (!items.length) return;
      e.preventDefault();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      mark();
    } else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); pick(items[active]); }
    else if (e.key === 'Escape') close();
  });
  list.addEventListener('mousedown', (e) => {
    const li = (e.target as HTMLElement).closest('li');
    if (li?.dataset.s) { e.preventDefault(); pick(li.dataset.s); }
  });
  input.addEventListener('blur', close);
}
