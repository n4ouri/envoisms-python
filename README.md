# EnvoiSMS Python SDK

[![PyPI version](https://img.shields.io/pypi/v/envoisms.svg)](https://pypi.org/project/envoisms/)
[![Python versions](https://img.shields.io/pypi/pyversions/envoisms.svg)](https://pypi.org/project/envoisms/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/n4ouri/envoisms-python/blob/main/LICENSE)

Official Python SDK for [EnvoiSMS.ma](https://envoisms.ma) — the direct-operator **SMS**, **WhatsApp Business (WABA)** and **OTP verification** API platform for Morocco (Maroc). One client, one API key, four channels.

```bash
pip install envoisms
```

## What is EnvoiSMS.ma?

EnvoiSMS.ma routes transactional and marketing messages through direct connections to Morocco's three mobile operators, plus the official WhatsApp Cloud API — no aggregator, no gray SIM routes.

| Channel | What it's for | Covered by this SDK |
| --- | --- | --- |
| [SMS Direct Opérateurs](https://envoisms.ma/fr/api-sms-maroc/) — IAM, Inwi, Orange | OTP codes, delivery alerts, marketing SMS, from 0.48 MAD/SMS | ✅ `send()`, `send_bulk()` |
| [WhatsApp Business API (Meta WABA)](https://envoisms.ma/fr/whatsapp-business-api-maroc/) | Approved templates, interactive buttons, catalog, multi-agent inbox, from 0.65 MAD/message | ✅ `send(channel="whatsapp")` |
| [OTP / 2FA Verification](https://envoisms.ma/fr/services/otp/) | Send + check one-time codes over SMS or WhatsApp | ✅ `send_otp()`, `check_otp()` |
| [Numéro Virtuel (+212)](https://envoisms.ma/fr/whatsapp/numero-virtuel/) | Cloud Moroccan business line, no physical SIM, shared team inbox | Manage from the [dashboard](https://envoisms.ma/fr/login/) |
| [Assistant IA Conversationnel](https://envoisms.ma/fr/whatsapp-ai-bot/) | Darija/French AI agent for COD order confirmation & support handoff | Manage from the [dashboard](https://envoisms.ma/fr/login/) |

Numéros Virtuels and the AI assistant are configured from your EnvoiSMS.ma dashboard today; dedicated SDK endpoints for them are on the roadmap. Everything below (`send`, OTP, billing, webhooks) works with the SDK right now.

## Quick Start — Send an SMS

```python
import os
from envoisms import EnvoiSMSClient

client = EnvoiSMSClient(api_key=os.getenv("ENVOISMS_API_KEY"))

response = client.send(
    to="+212600000000",
    message="Votre code de vérification est 492018",
    from_sender="MonBusiness",  # validated Sender ID, or omit to use your default
)

print(f"Message ID: {response['id']}")  # poll it with get_message(), match it in webhooks
```

Every `send()` / `send_bulk()` carries an `Idempotency-Key` (generated, or pass `idempotency_key=`), so a retry after a timeout can never bill the same message twice.

## Choosing a channel: SMS or WhatsApp?

**Default to SMS.** It reaches every Moroccan mobile (IAM, Inwi, Orange) with no setup beyond your API key, and it is what an "ordinary text to a customer" needs — even when that customer uses WhatsApp.

`channel="whatsapp"` is different in kind, not just in name. It sends from **your own WhatsApp Business number**, which means:

- the number must be connected in your dashboard (WhatsApp tab) — otherwise the API answers `403 WHATSAPP_NOT_CONNECTED` and nothing is charged;
- a free-form text is only accepted while the recipient has written to that number in the last 24 hours (`400 OUT_OF_24H_WINDOW` otherwise, nothing charged);
- outside that window, you send an **approved template** (`template` field), not free text.

| You want to… | Use |
| --- | --- |
| Send a text to a customer (order status, reminder, alert) | `channel="sms"` (the default — just omit it) |
| Send a one-time code | `send_otp()` — pass `channel="whatsapp"` for a WhatsApp code through our shared sender, no connection needed |
| Reply on WhatsApp to a customer who wrote to your number in the last 24 h | `channel="whatsapp"` with `message` |
| Start a WhatsApp conversation (marketing, utility) | `channel="whatsapp"` with an approved `template` |

Common mistake: sending an SMS-style text with `channel="whatsapp"` "because the customer is on WhatsApp". Both refusals above name the fix — send it as SMS.

## Send a WhatsApp Business Message

Only from a WhatsApp Business number you connected in your [dashboard](https://envoisms.ma/fr/whatsapp/) — see the table above. Free text works inside the 24-hour customer window; otherwise send an approved template.

```python
# Reply to a customer who wrote to your number in the last 24 h
response = client.send(
    to="+212600000000",
    message="Bonjour ! Votre commande #89240 a été expédiée.",
    channel="whatsapp",
)

# Start the conversation yourself: approved template, any time
response = client.send(
    to="+212600000000",
    message="Votre commande #89240 a été expédiée.",  # shown in your history; the template body is what goes out
    channel="whatsapp",
    template={"name": "order_shipped", "language": "fr", "variables": ["89240"]},
)
```

### Automatic channel fallback (cascade)

Send over WhatsApp and drop back to SMS automatically when a number is unreachable or has no WhatsApp — the same fallback used for VTC riders on flaky mobile data.

```python
response = client.send(
    to="+212600000000",
    message="Votre chauffeur arrive dans 2 minutes.",
    channel="whatsapp",
    cascade=True,
)
```

## OTP / 2FA Verification

```python
# 1. Send OTP (channel="sms" by default; pass channel="whatsapp" to send over WhatsApp instead)
otp_res = client.send_otp(
    to="+212600000000",
    brand="MonBusiness",
    code_length=6,
    expiry=600,  # seconds
)

session_id = otp_res["session_id"]

# 2. Verify the code the user typed in
check_res = client.check_otp(session_id=session_id, code="492018")

if check_res.get("verified"):
    print("OTP code is valid!")

# Optional: inspect a session's status without consuming an attempt
session = client.get_otp_session(session_id)
```

## Bulk Sending

```python
client.send_bulk(
    messages=[
        {"to": "+212600000001", "message": "Promo -20% ce week-end"},
        {"to": "+212600000002", "message": "Promo -20% ce week-end"},
    ],
    from_sender="MonBusiness",
)
```

## Message Status & Delivery

```python
status = client.get_message(message_id="msg_123")
recent = client.list_messages(limit=50, offset=0)
```

## Verifying Delivery Webhooks (DLR)

If you configure a delivery-status webhook, verify its `X-EnvoiSMS-Signature` header before trusting the payload:

```python
from envoisms import EnvoiSMSClient

is_valid = EnvoiSMSClient.verify_webhook_signature(
    raw_body=request.body,             # raw request bytes/string, not parsed JSON
    signature_header=request.headers["X-EnvoiSMS-Signature"],
    secret=os.getenv("ENVOISMS_WEBHOOK_SECRET"),
)
```

## Account & Billing

```python
balance = client.get_balance()
packs = client.list_packs()
payment_methods = client.list_payment_methods()

client.create_topup(amount_mad=200, payment_method="stripe")
```

## Analytics & API Keys

```python
stats = client.analytics(days=30)
new_key = client.create_api_key(name="Server key", scope="live")
```

## Compliance: Opt-outs (STOP)

```python
client.create_optout(phone="+212600000000")
```

## Error Handling & Retries

The client retries `5xx` responses and network errors up to `max_retries` times (default 2) with exponential backoff, and raises `EnvoiSMSError` — with `status_code` and `code` attributes — on any failure:

```python
from envoisms import EnvoiSMSClient, EnvoiSMSError

client = EnvoiSMSClient(api_key=os.getenv("ENVOISMS_API_KEY"), max_retries=3, timeout=20)

try:
    client.send(to="+212600000000", message="Test")
except EnvoiSMSError as e:
    print(f"Send failed ({e.status_code} {e.code}): {e}")
```

## Why teams pick EnvoiSMS.ma over an aggregator

- **Direct routes to IAM, Inwi and Orange** — no international transit hop, no gray-route ban risk.
- **2.4–2.8 second OTP latency**, measured across IAM, Inwi and Orange — aggregators routing through Europe typically land in the 10s+ range.
- **Billing in MAD**, no EUR/USD conversion surprises.
- **Local support** based in Casablanca, not an offshore ticket queue.

See the full breakdown on [envoisms.ma](https://envoisms.ma).

## Documentation & Pricing

- Full API reference: [envoisms.ma/fr/docs](https://envoisms.ma/fr/docs/)
- Pricing & credit packs: [envoisms.ma/fr/tarifs](https://envoisms.ma/fr/tarifs/)
- Real customer use cases: [envoisms.ma/fr/cas-usage](https://envoisms.ma/fr/cas-usage)
- Create a free account (5 MAD credit included): [envoisms.ma/fr/register](https://envoisms.ma/fr/register/)

## Other official SDKs

- Node.js / TypeScript: [`npm install envoisms`](https://www.npmjs.com/package/envoisms)
- PHP: [`composer require envoisms/envoisms-php`](https://packagist.org/packages/envoisms/envoisms-php)
- WooCommerce, Shopify, Zapier and Google Sheets integrations: [envoisms.ma/fr/integrations](https://envoisms.ma/fr/integrations/)

## Support

- Email: [support@envoisms.ma](mailto:support@envoisms.ma)
- Sales: [sales@envoisms.ma](mailto:sales@envoisms.ma)

## License

MIT
