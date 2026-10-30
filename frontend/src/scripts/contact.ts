import { loadTurnstile } from '../lib/turnstile';
import { ui } from '../i18n/ui';
const form = document.querySelector<HTMLFormElement>('[data-contact]');
if (form) {
  let token = '', widget = '';
  const status = form.querySelector<HTMLElement>('[role="status"]')!;
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]')!;
  if (form.dataset.sitekey) {
    const observer = new IntersectionObserver(async entries => {
      if (!entries.some(e=>e.isIntersecting)) return;
      observer.disconnect();
      try {
        await loadTurnstile();
        widget = window.turnstile!.render(form.querySelector<HTMLElement>('[data-contact-turnstile]')!, { sitekey: form.dataset.sitekey!, action: 'contact', theme: 'dark', callback: value => { token = value; }, 'expired-callback': () => { token = ''; }, 'error-callback': () => { token = ''; status.textContent = ui.verify; } });
      } catch { status.textContent = ui.verify; }
    }, { rootMargin: '300px' });
    observer.observe(form);
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (form.dataset.sitekey && !token) { status.textContent = ui.verify; return; }
    button.disabled = true; status.textContent = ui.sending;
    let failureMessage = ui.error;
    try {
      const payload = Object.fromEntries(new FormData(form));
      const response = await fetch('/api/public/contact', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...payload, turnstile_token: token }), signal: AbortSignal.timeout(20000) });
      const result = await response.json();
      if (!response.ok) { failureMessage = result.error || ui.error; throw new Error(failureMessage); }
      status.textContent = form.dataset.success || ''; form.reset();
      window.umami?.track('contact-submit'); window.plausible?.('contact-submit');
    } catch { status.textContent = failureMessage; }
    finally { button.disabled = false; token = ''; if (widget) window.turnstile?.reset(widget); }
  });
}
