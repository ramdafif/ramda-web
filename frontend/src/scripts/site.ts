declare global { interface Window { umami?: { track: (name: string) => void }; plausible?: (name: string) => void; } }
document.addEventListener('click', event => {
  const target = (event.target as Element).closest<HTMLElement>('[data-track]');
  if (target?.dataset.track) { window.umami?.track(target.dataset.track); window.plausible?.(target.dataset.track); }
  const menuLink = (event.target as Element).closest('.mobile-menu a');
  if (menuLink) document.querySelector<HTMLDetailsElement>('.mobile-menu')?.removeAttribute('open');
});
export {};
