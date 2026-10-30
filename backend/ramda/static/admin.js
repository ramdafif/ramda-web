/* All behavior is local and CSP-safe; untrusted strings are rendered with textContent. */
const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
document.addEventListener('htmx:configRequest', event => { event.detail.headers['X-CSRFToken'] = csrf; });
async function api(url, body) {
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: JSON.stringify(body) });
  if (!response.ok) throw new Error('Tidak dapat menyimpan. Muat ulang lalu coba lagi.');
  return response.json();
}
const list = document.querySelector('[data-sortable-url]');
if (list && list.dataset.filtered === 'false') {
  const saveOrder = async () => {
    const status = document.getElementById('reorder-status');
    try { await api(list.dataset.sortableUrl, { ids: [...list.querySelectorAll('[data-id]')].map(x => Number(x.dataset.id)) }); status.textContent = 'Urutan draf disimpan. Publish untuk menayangkan.'; }
    catch (error) { status.textContent = error.message; }
  };
  if (window.Sortable) new Sortable(list, { handle: '.drag-handle', animation: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 150, onEnd: saveOrder });
  list.addEventListener('click', event => {
    const button = event.target.closest('.move-up,.move-down');
    if (!button) return;
    const row = button.closest('[data-id]');
    if (button.classList.contains('move-up') && row.previousElementSibling) list.insertBefore(row, row.previousElementSibling);
    if (button.classList.contains('move-down') && row.nextElementSibling) list.insertBefore(row.nextElementSibling, row);
    saveOrder();
  });
}
document.querySelectorAll('[data-copy-media]').forEach(button => button.addEventListener('click', async () => {
  const value = button.parentElement.querySelector('textarea').value;
  await navigator.clipboard.writeText(value); button.textContent = 'Referensi disalin';
}));
const form = document.querySelector('.editor-form');
if (form) {
  const schema = JSON.parse(form.dataset.schema);
  const values = JSON.parse(form.dataset.values);
  const target = document.getElementById('enhanced-editor');
  const basic = document.getElementById('basic-editor');
  let editors = [];
  let counter = 0;
  const resolve = spec => spec.$ref ? schema.$defs[spec.$ref.split('/').pop()] : spec;
  const human = key => key.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
  function element(tag, attrs = {}, content = '') {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, value);
    if (content) node.textContent = content;
    return node;
  }
  function blank(input) {
    const spec = resolve(input);
    if (spec.default !== undefined) return structuredClone(spec.default);
    if (spec.enum) return spec.enum[0];
    if (spec.type === 'object') return Object.fromEntries(Object.entries(spec.properties || {}).map(([k, v]) => [k, blank(v)]));
    if (spec.type === 'array') return [];
    if (spec.type === 'boolean') return false;
    if (['number', 'integer'].includes(spec.type)) return spec.minimum || 0;
    return '';
  }
  function field(name, input, value, set, path) {
    const spec = resolve(input);
    if (value === undefined || value === null) { value = blank(input); set(value); }
    const wrapper = element('div');
    const title = human(name);
    if (spec.type === 'object' && spec.properties) {
      wrapper.className = 'nested';
      const heading = element('p', { class: 'field-title' }, title); wrapper.append(heading);
      if (input.$ref?.endsWith('/ImageRef')) {
        const paste = element('details'); paste.append(element('summary', {}, 'Tempel referensi dari Media'));
        const text = element('textarea', { rows: 3, 'aria-label': 'Referensi media JSON' });
        const button = element('button', { type: 'button', class: 'ghost' }, 'Gunakan media');
        button.addEventListener('click', () => { try { const media = JSON.parse(text.value); if (!media.src || !media.alt) throw new Error(); set(media); render(); } catch { text.setCustomValidity('Referensi media tidak valid'); text.reportValidity(); } });
        paste.append(text, button); wrapper.append(paste);
      }
      for (const [key, child] of Object.entries(spec.properties)) wrapper.append(field(key, child, value[key], next => { value[key] = next; set(value); }, `${path}.${key}`));
      return wrapper;
    }
    if (spec.type === 'array') {
      wrapper.append(element('p', { class: 'field-title' }, title));
      value.forEach((item, i) => {
        const box = element('div', { class: 'repeat-item' });
        box.append(field(`${title} ${i + 1}`, spec.items || {}, item, next => { value[i] = next; set(value); }, `${path}.${i}`));
        const buttons = element('div', { class: 'inline-actions' });
        const remove = element('button', { type: 'button', class: 'ghost danger' }, 'Hapus item');
        remove.addEventListener('click', () => { value.splice(i, 1); set(value); render(); });
        const up = element('button', { type: 'button', class: 'ghost', 'aria-label': 'Naikkan item' }, '↑');
        up.addEventListener('click', () => { if (i > 0) { [value[i - 1], value[i]] = [value[i], value[i - 1]]; set(value); render(); } });
        buttons.append(up, remove); box.append(buttons); wrapper.append(box);
      });
      const add = element('button', { type: 'button', class: 'ghost' }, '+ Tambah item');
      add.addEventListener('click', () => { value.push(blank(spec.items || {})); set(value); render(); }); wrapper.append(add);
      return wrapper;
    }
    const id = `cms-field-${counter++}`;
    const label = element('label', { for: id }, name === 'id' ? 'Indonesia' : name === 'en' ? 'English (opsional)' : title);
    let control;
    if (spec.type === 'boolean') {
      label.className = 'check'; control = element('input', { type: 'checkbox', id }); control.checked = !!value;
      control.addEventListener('change', () => set(control.checked));
    } else if (spec.enum) {
      control = element('select', { id });
      spec.enum.forEach(option => control.append(element('option', { value: option }, human(option))));
      control.value = value; control.addEventListener('change', () => set(control.value));
    } else if (spec.type === 'object' || (!spec.type && typeof value === 'object')) {
      control = element('textarea', { id, rows: 5, class: 'json-fallback' }); control.value = JSON.stringify(value, null, 2);
      control.addEventListener('input', () => { try { set(JSON.parse(control.value)); control.setCustomValidity(''); } catch { control.setCustomValidity('JSON tidak valid'); } });
    } else {
      const long = /(?:body|bio|problem|solution|result|answer|prompt|description|headline|quote)/.test(path);
      control = long ? element('textarea', { id, rows: 4 }) : element('input', { id, type: ['number', 'integer'].includes(spec.type) ? 'number' : 'text' });
      if (spec.type === 'number') control.step = 'any';
      if (spec.minimum !== undefined) control.min = spec.minimum;
      if (spec.maximum !== undefined) control.max = spec.maximum;
      if (spec.maxLength) control.maxLength = spec.maxLength;
      control.value = value;
      control.addEventListener('input', () => set(['number', 'integer'].includes(spec.type) ? Number(control.value) : control.value));
      if (/(?:body|bio|problem|solution|result|answer)\.(id|en)$/.test(path) && window.EasyMDE) {
        control.dataset.markdown = 'true'; control._setValue = set;
      }
    }
    label.append(control); wrapper.append(label); return wrapper;
  }
  function render() {
    editors.forEach(editor => editor.toTextArea()); editors = []; counter = 0; target.replaceChildren();
    for (const [name, spec] of Object.entries(schema.properties)) {
      const group = element('fieldset', { class: 'card fieldset' }); group.append(element('legend', {}, human(name)));
      group.append(field(name, spec, values[name], value => { values[name] = value; }, name)); target.append(group);
    }
    target.querySelectorAll('[data-markdown]').forEach(textarea => {
      const editor = new EasyMDE({ element: textarea, spellChecker: false, status: false, autoDownloadFontAwesome: false, minHeight: '140px', toolbar: ['bold', 'italic', 'heading', '|', 'unordered-list', 'ordered-list', 'link', '|', 'preview'], previewRender: (plain, preview) => { api('/admin/markdown-preview', { text: plain }).then(data => { preview.innerHTML = data.html; }).catch(() => { preview.textContent = 'Pratinjau belum tersedia.'; }); return ''; } });
      editor.codemirror.on('change', () => textarea._setValue(editor.value())); editors.push(editor);
    });
  }
  try {
    render(); basic.hidden = true; basic.querySelectorAll('input,textarea,select').forEach(input => { input.disabled = true; });
    const hidden = element('input', { type: 'hidden', name: 'content_json' }); form.append(hidden);
    form.addEventListener('submit', () => { hidden.value = JSON.stringify(values); });
  } catch { target.replaceChildren(); basic.hidden = false; }
}
