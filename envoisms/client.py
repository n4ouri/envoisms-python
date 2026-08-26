import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional
import requests


class EnvoiSMSError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class EnvoiSMSClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.envoisms.ma",
        max_retries: int = 2,
        timeout: int = 15,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "EnvoiSMS-PythonSDK/1.0.0",
        })

    # --- Messages ---
    def send(
        self,
        to: str,
        message: str,
        from_sender: Optional[str] = None,
        channel: str = "sms",
        cascade: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"to": to, "message": message, "channel": channel, "cascade": cascade}
        if from_sender:
            payload["from"] = from_sender
        if metadata:
            payload["metadata"] = metadata
        return self._request("POST", "/v1/messages", json=payload)

    def send_bulk(
        self,
        messages: List[Dict[str, Any]],
        from_sender: Optional[str] = None,
        channel: str = "sms",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"messages": messages, "channel": channel}
        if from_sender:
            payload["from"] = from_sender
        return self._request("POST", "/v1/messages/bulk", json=payload)

    def get_message(self, message_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/messages/{message_id}")

    def list_messages(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self._request("GET", f"/v1/messages?limit={limit}&offset={offset}")

    # --- Verify / OTP ---
    def send_otp(
        self,
        to: str,
        channel: str = "sms",
        brand: Optional[str] = None,
        code_length: int = 6,
        expiry: int = 300,
        app_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "to": to,
            "channel": channel,
            "code_length": code_length,
            "expiry": expiry,
        }
        if brand:
            payload["brand"] = brand
        if app_id:
            payload["app_id"] = app_id
        return self._request("POST", "/v1/verify/send", json=payload)

    def check_otp(self, session_id: str, code: str) -> Dict[str, Any]:
        return self._request("POST", "/v1/verify/check", json={"session_id": session_id, "code": code})

    def get_otp_session(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/verify/{session_id}")

    # --- Billing & Balance ---
    def get_balance(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/billing/balance")

    def list_packs(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/billing/packs")

    # --- Webhook Signature Verification ---
    @staticmethod
    def verify_webhook_signature(
        raw_body: str,
        signature_header: str,
        secret: str,
        tolerance_seconds: int = 300,
    ) -> bool:
        if not raw_body or not signature_header or not secret:
            return False

        # Handles timestamped header format: t=1234567890,v1=abcdef...
        if "t=" in signature_header and "v1=" in signature_header:
            parts = dict(item.strip().split("=", 1) for item in signature_header.split(","))
            timestamp_str = parts.get("t")
            signature = parts.get("v1")

            if not timestamp_str or not signature:
                return False

            try:
                timestamp = int(timestamp_str)
            except ValueError:
                return False

            now = int(time.time())
            if abs(now - timestamp) > tolerance_seconds:
                return False

            payload = f"{timestamp}.{raw_body}".encode("utf-8")
            expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected)

        # Handles direct sha256=... format
        clean_sig = signature_header.removeprefix("sha256=")
        expected = hmac.new(secret.encode("utf-8"), raw_body.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(clean_sig, expected)

    # --- Internal Request with Retry ---
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    f"{self.base_url}{path}",
                    timeout=self.timeout,
                    **kwargs,
                )
                if response.status_code >= 500 and attempt < self.max_retries:
                    time.sleep(2 ** attempt * 0.5)
                    continue

                data = response.json()
                if response.status_code >= 400:
                    raise EnvoiSMSError(
                        data.get("error", {}).get("message", f"EnvoiSMS API error ({response.status_code})"),
                        status_code=response.status_code,
                        code=data.get("error", {}).get("code"),
                    )
                return data
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt * 0.5)
                    continue
                break

        raise EnvoiSMSError(f"Request failed: {last_error}")
