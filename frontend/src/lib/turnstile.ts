type Options = { sitekey: string; action: string; theme: string; callback: (token: string) => void; 'expired-callback': () => void; 'error-callback': () => void; };
declare global { interface Window { turnstile?: { render: (node: HTMLElement, options: Options) => string; reset: (id: string) => void; remove: (id: string) => void; }; } }
let ready: Promise<void> | undefined;
export async function loadTurnstile() {
  if (window.turnstile) return;
  ready ||= new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'; script.async = true; script.defer = true;
    script.onload = () => resolve(); script.onerror = () => { ready = undefined; reject(new Error('verify')); };
    document.head.append(script);
  });
  return ready;
}
