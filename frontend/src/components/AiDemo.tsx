import { useEffect, useRef, useState } from 'react';
import { text, type RecordData, type Localized } from '../lib/cms';
import { loadTurnstile } from '../lib/turnstile';
import { ui } from '../i18n/ui';
type Message = { role: 'user' | 'assistant'; content: string };
export default function AiDemo({ config, sitekey, name }: { config: RecordData; sitekey: string; name: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [verification, setVerification] = useState('');
  const [sessionToken, setSessionToken] = useState('');
  const [turns, setTurns] = useState(0);
  const challenge = useRef<HTMLDivElement>(null);
  const widgetId = useRef('');
  const log = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!sitekey || !challenge.current) return;
    let widget = '', mounted = true;
    loadTurnstile().then(() => { if (mounted && challenge.current) widget = widgetId.current = window.turnstile!.render(challenge.current, { sitekey, action: 'ai', theme: 'dark', callback: setVerification, 'expired-callback': () => setVerification(''), 'error-callback': () => setError(ui.verify) }); }).catch(() => setError(ui.verify));
    return () => { mounted = false; if (widget) window.turnstile?.remove(widget); };
  }, [sitekey]);
  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [messages]);
  async function send(message: string) {
    if (busy || !message.trim() || turns >= config.max_turns) return;
    if (sitekey && !sessionToken && !verification) { setError(ui.verify); return; }
    const history = messages.filter(m=>m.content.trim()).slice(-10);
    setInput(''); setBusy(true); setError('');
    setMessages(previous => [...previous, { role: 'user', content: message }, { role: 'assistant', content: '' }]);
    try {
      const response = await fetch('/api/public/ai/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, history, turnstile_token: verification, session_token: sessionToken }), signal: AbortSignal.timeout(60000) });
      if (!response.ok) { const data = await response.json(); throw new Error(data.error === 'limit' ? text(config.limit_message) : text(config.offline_message)); }
      if (!response.body) throw new Error(text(config.offline_message));
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '', answer = '';
      while (true) {
        const chunk = await reader.read(); if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        let boundary;
        while ((boundary = buffer.indexOf('\n\n')) !== -1) {
          const event = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
          const type = event.match(/^event: (.+)$/m)?.[1];
          const data = JSON.parse(event.match(/^data: (.+)$/m)?.[1] || '{}');
          if (type === 'session') setSessionToken(data.token);
          if (type === 'token') { answer += data.text; setMessages(previous => [...previous.slice(0, -1), { role: 'assistant', content: answer }]); }
          if (type === 'error') throw new Error(text(config.offline_message));
        }
      }
      setTurns(t => t + 1);
    } catch (failure) { setError(failure instanceof Error ? failure.message : text(config.offline_message)); }
    finally { setBusy(false); if (sitekey && !sessionToken && widgetId.current) { setVerification(''); window.turnstile?.reset(widgetId.current); } }
  }
  return <div className="ai-panel"><div className="ai-info"><span className="icon-box" aria-hidden="true">✳</span><h3>{name}</h3><p>{text(config.welcome_message)}</p><div className="ai-chips">{config.suggestions?.map((suggestion: Localized, i: number) => <button key={i} type="button" onClick={()=>send(text(suggestion))} disabled={busy || turns >= config.max_turns}>{text(suggestion)}</button>)}</div></div><div className="ai-chat"><div className="messages" ref={log} role="log" aria-live="polite" aria-relevant="additions text">{messages.map((m,i)=><div key={i} className={`chat-message ${m.role}`}>{m.content || (busy ? ui.wait : '')}</div>)}</div><div ref={challenge} hidden={!!sessionToken}></div><form className="ai-input" onSubmit={e=>{e.preventDefault();send(input);}}><label className="honey" htmlFor="ai-question">{text(config.input_placeholder)}</label><input id="ai-question" value={input} onChange={e=>setInput(e.target.value)} maxLength={config.max_input_chars} placeholder={text(config.input_placeholder)} disabled={busy || turns >= config.max_turns} required/><button className="button" disabled={busy || turns >= config.max_turns} type="submit">{ui.send}</button></form>{error && <p className="ai-error" role="status">{error}</p>}{turns >= config.max_turns && <p className="ai-error">{text(config.limit_message)}</p>}<p className="ai-disclaimer">{text(config.disclaimer)}</p></div></div>;
}
