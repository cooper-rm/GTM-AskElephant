"""
Delivery Layer

Each delivery function:
  1. Attempts real delivery if integration env vars are set
  2. Falls back to log+persist if env vars missing
  3. ALWAYS writes to disk for audit
  4. Retries transient failures (3 attempts, exponential backoff)

Environment variables:
    SLACK_WEBHOOK_URL           — #closed-won-announcements
    SLACK_BRIEF_WEBHOOK_URL     — #customer-success-briefings
    SLACK_PLAN_WEBHOOK_URL      — #30d-customer-success-plans
    SLACK_KICKOFF_WEBHOOK_URL   — #kickoff-drafts
    GMAIL_USER                  — Gmail sender (welcome email)
    GMAIL_APP_PASSWORD          — Gmail app password
    HUBSPOT_API_KEY             — HubSpot token (CRM updates)
"""
import os
import json
import time
from datetime import datetime, timezone

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "../../../.env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
except ImportError:
    pass

import urllib.request
import urllib.error
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../../data/runs")

MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 3, 9]  # exponential: 1s, 3s, 9s


def _with_retry(fn, *args, **kwargs) -> dict:
    """
    Retry a delivery function up to MAX_RETRIES times on transient failure.
    The function must return a dict with a 'status' key.
    Only retries on 'failed' status — 'sent', 'log_only' are returned immediately.
    """
    last_result = {}
    for attempt in range(MAX_RETRIES):
        last_result = fn(*args, **kwargs)
        if last_result.get('status') != 'failed':
            return last_result
        if attempt < MAX_RETRIES - 1:
            delay = BACKOFF_SECONDS[attempt]
            print(f"[retry] {fn.__name__} failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                  f"retrying in {delay}s: {last_result.get('error', '')[:80]}")
            time.sleep(delay)
    return last_result


# ── Gmail SMTP sender ──────────────────────────────────────────────────────

def _send_gmail(
    to_email: str,
    subject: str,
    body: str,
    attachments: "list[tuple[str, bytes, str]] | None" = None,
) -> dict:
    """
    Send email via Gmail SMTP.
    attachments: list of (filename, content_bytes, mime_type) tuples.
    """
    gmail_user = os.environ.get('GMAIL_USER', '').strip()
    # Google displays app passwords with spaces, SMTP wants them stripped
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '').replace(' ', '').strip()

    if not gmail_user or not gmail_password:
        return {'status': 'log_only', 'note': 'GMAIL_USER / GMAIL_APP_PASSWORD not set'}

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    for fname, fdata, mime_type in (attachments or []):
        maintype, subtype = mime_type.split('/', 1)
        part = MIMEBase(maintype, subtype)
        part.set_payload(fdata)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{fname}"',
        )
        msg.attach(part)

    def _attempt():
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as server:
                server.login(gmail_user, gmail_password)
                server.sendmail(gmail_user, [to_email], msg.as_string())
            return {'status': 'sent', 'mode': 'live', 'from': gmail_user, 'to': to_email}
        except Exception as e:
            return {'status': 'failed', 'mode': 'live', 'error': str(e)}

    return _with_retry(_attempt)


def _parse_subject_and_body(content: str, subject_fallback: str) -> tuple[str, str]:
    """Extract 'Subject: ...' line from content, return (subject, body)."""
    lines = content.strip().split('\n')
    subject = subject_fallback
    body_start = 0
    for i, line in enumerate(lines[:3]):
        stripped = line.strip()
        if stripped.lower().startswith('subject:'):
            subject = stripped.split(':', 1)[1].strip()
            body_start = i + 1
            break
    body = '\n'.join(lines[body_start:]).strip()
    return subject, body


def _log(deal_id: str, artifact_type: str, destination: str, content_preview: str):
    """Print a delivery receipt to terminal."""
    preview = content_preview[:120].replace('\n', ' ')
    if len(content_preview) > 120:
        preview += '...'
    print(f"[DELIVERY] {deal_id} | {artifact_type:16s} | {destination:30s} | {preview}")


def _save_artifact(deal_id: str, artifact_type: str, content, delivery_info: dict) -> str:
    """Persist artifact to disk for audit."""
    run_dir = os.path.join(OUTPUT_DIR, deal_id)
    os.makedirs(run_dir, exist_ok=True)
    record = {
        'deal_id': deal_id,
        'artifact_type': artifact_type,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'delivery': delivery_info,
        'content': content,
    }
    path = os.path.join(run_dir, f"{artifact_type}.json")
    with open(path, 'w') as f:
        json.dump(record, f, indent=2)
    return path


def _log_and_save(deal_id: str, artifact_type: str, content, delivery_info: dict) -> dict:
    """Log to terminal + save to disk. Shared by all delivery functions."""
    content_str = content if isinstance(content, str) else json.dumps(content)
    destination = delivery_info.get('destination', 'unknown')
    _log(deal_id, artifact_type, destination, content_str)
    path = _save_artifact(deal_id, artifact_type, content, delivery_info)
    return {'status': 'logged', 'path': path, **delivery_info}


# ── Public delivery functions ──────────────────────────────────────────────

def send_email(
    deal_id: str,
    recipient: str,
    content: str,
    subject_hint: str = '',
    attachments: "list[tuple[str, bytes, str]] | None" = None,
) -> dict:
    """
    Send customer welcome email via Gmail SMTP.
    attachments: list of (filename, bytes, mime_type) — e.g. invoice PDF.
    """
    subject, body = _parse_subject_and_body(
        content, subject_fallback=subject_hint or 'Welcome to AskElephant'
    )
    delivery_info = {
        'destination': f'email → {recipient}',
        'recipient': recipient,
        'subject': subject,
        'attachments': [fname for fname, _, _ in (attachments or [])],
    }
    send_result = _send_gmail(recipient, subject, body, attachments=attachments)
    delivery_info.update(send_result)

    _log(deal_id, 'welcome_email', delivery_info['destination'], content)
    path = _save_artifact(deal_id, 'welcome_email', content, delivery_info)
    return {'path': path, **delivery_info}


def _post_to_slack_webhook(webhook_url: str, content) -> dict:
    """
    Send a message to a Slack webhook URL. Returns delivery status dict.
    content: either a plain text string (posted as {"text": content}) OR a
    Block Kit dict. When a dict, only Slack-accepted keys are forwarded —
    extra keys like "structured" are dropped so they don't break the webhook.
    """
    if not webhook_url:
        return {'mode': 'log_only', 'status': 'log_only', 'note': 'webhook URL not set'}

    if isinstance(content, dict):
        slack_keys = {
            'text', 'blocks', 'attachments', 'thread_ts', 'mrkdwn',
            'unfurl_links', 'unfurl_media',
            'icon_emoji', 'icon_url', 'username',
        }
        payload_obj = {k: v for k, v in content.items() if k in slack_keys}
    else:
        payload_obj = {'text': content}

    payload = json.dumps(payload_obj).encode('utf-8')
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={'Content-Type': 'application/json'},
    )

    def _attempt():
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {
                    'mode': 'live',
                    'status': 'sent',
                    'http_status': resp.status,
                    'response': resp.read().decode('utf-8'),
                }
        except urllib.error.HTTPError as e:
            return {
                'mode': 'live',
                'status': 'failed',
                'error': f'HTTP {e.code}: {e.read().decode("utf-8", errors="ignore")}',
            }
        except Exception as e:
            return {'mode': 'live', 'status': 'failed', 'error': str(e)}

    return _with_retry(_attempt)


def post_slack(deal_id: str, channel: str, content, artifact_type: str = 'slack_announce',
               webhook_env: str = 'SLACK_WEBHOOK_URL') -> dict:
    """
    Post to Slack channel via Incoming Webhook specified by env var.
    content: str (plain mrkdwn) OR dict with {"blocks": [...], "text": fallback}.
    """
    webhook_url = os.environ.get(webhook_env, '').strip()
    delivery_info = {
        'destination': f'slack → {channel}',
        'channel': channel,
        'webhook_env': webhook_env,
    }

    result = _post_to_slack_webhook(webhook_url, content)
    delivery_info.update(result)

    # Terminal log preview — use fallback text for Block Kit payloads
    preview = content.get('text', '') if isinstance(content, dict) else content
    _log(deal_id, artifact_type, delivery_info['destination'], preview)
    path = _save_artifact(deal_id, artifact_type, content, delivery_info)
    return {'path': path, **delivery_info}


def save_csm_brief(deal_id: str, content) -> dict:
    """Post CSM brief to #customer-success-briefings Slack channel.
    Content may be a string (legacy) or a Block Kit dict with a built-in header.
    """
    return post_slack(
        deal_id,
        '#customer-success-briefings',
        content,
        artifact_type='csm_brief',
        webhook_env='SLACK_BRIEF_WEBHOOK_URL',
    )


def save_success_plan(deal_id: str, content) -> dict:
    """Post recommended 30-day success plan to #30d-customer-success-plans."""
    return post_slack(
        deal_id,
        '#30d-customer-success-plans',
        content,
        artifact_type='success_plan',
        webhook_env='SLACK_PLAN_WEBHOOK_URL',
    )


def save_kickoff_draft(deal_id: str, content) -> dict:
    """Post kickoff meeting request draft to #kickoff-drafts for CSM review."""
    return post_slack(
        deal_id,
        '#kickoff-drafts',
        content,
        artifact_type='kickoff_draft',
        webhook_env='SLACK_KICKOFF_WEBHOOK_URL',
    )


def push_crm_updates(deal_id: str, updates: dict) -> dict:
    """Push CRM field updates."""
    return _log_and_save(deal_id, 'crm_updates', updates, {
        'destination': 'hubspot → deal record',
        'crm': 'hubspot',
    })


def send_handoff_package(
    deal_id: str,
    recipient: str,
    subject: str,
    body: str,
    pdfs: list,
) -> dict:
    """
    Email the full handoff package to a CSM. Subject + body are composed
    upstream so the email can embed real customer/deal context.
    pdfs: list of (filename, bytes) tuples — typically brief, plan, kickoff.
    """
    attachments = [(fname, fbytes, 'application/pdf') for fname, fbytes in pdfs]
    attachment_names = [fname for fname, _ in pdfs]

    delivery_info = {
        'destination': f'email → {recipient} (handoff package)',
        'recipient': recipient,
        'subject': subject,
    }
    send_result = _send_gmail(recipient, subject, body, attachments=attachments)
    delivery_info.update(send_result)
    delivery_info['attachments'] = attachment_names

    # The artifact "content" is the package manifest — what files were bundled
    # and the email body used. PDF bytes live on disk separately.
    content = {
        'subject': subject,
        'body': body,
        'attachments': attachment_names,
    }
    _log(deal_id, 'handoff_package', delivery_info['destination'],
         f"bundle: {', '.join(attachment_names)}")
    path = _save_artifact(deal_id, 'handoff_package', content, delivery_info)
    return {'path': path, **delivery_info}
