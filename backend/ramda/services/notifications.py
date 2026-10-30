import smtplib
import ssl
from email.message import EmailMessage
import httpx
from flask import current_app


def notify_lead(lead):
    config = current_app.config
    outcomes = []
    text = f'Lead baru dari situs RAMDA\n\nNama: {lead.name}\nKontak: {lead.contact}\nJenis: {lead.project_type}\nAnggaran: {lead.budget_range}\n\n{lead.message}'
    if config['TELEGRAM_BOT_TOKEN'] and config['TELEGRAM_CHAT_ID']:
        try:
            response = httpx.post(f"https://api.telegram.org/bot{config['TELEGRAM_BOT_TOKEN']}/sendMessage", json={'chat_id': config['TELEGRAM_CHAT_ID'], 'text': text[:4000]}, timeout=5)
            response.raise_for_status()
            outcomes.append('sent' if response.json().get('ok') else 'failed')
        except (httpx.HTTPError, ValueError):
            outcomes.append('failed')
    if config['SMTP_HOST'] and config['NOTIFY_EMAIL'] and config['SMTP_FROM']:
        try:
            message = EmailMessage()
            message['Subject'] = 'Lead proyek baru · RAMDA'
            message['From'] = config['SMTP_FROM']
            message['To'] = config['NOTIFY_EMAIL']
            message.set_content(text)
            with smtplib.SMTP(config['SMTP_HOST'], config['SMTP_PORT'], timeout=5) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if config['SMTP_USER']:
                    smtp.login(config['SMTP_USER'], config['SMTP_PASSWORD'])
                smtp.send_message(message)
            outcomes.append('sent')
        except (smtplib.SMTPException, OSError):
            outcomes.append('failed')
    return 'sent' if 'sent' in outcomes else 'failed' if outcomes else 'unconfigured'
