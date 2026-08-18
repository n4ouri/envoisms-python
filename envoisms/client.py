from typing import Any, Dict, List, Optional
import requests


class EnvoiSMSClient:
    def __init__(self, api_key: str, base_url: str = "https://api.envoisms.ma"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def send(self, to: str, message: str, **kwargs: Any) -> Dict[str, Any]:
        payload = {"to": to, "message": message, **kwargs}
        return self._request("POST", "/v1/messages", json=payload)

    def send_bulk(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        payload = {"messages": messages, **kwargs}
        return self._request("POST", "/v1/messages/bulk", json=payload)

    def get_message(self, message_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/messages/{message_id}")

    def send_otp(self, to: str, **kwargs: Any) -> Dict[str, Any]:
        payload = {"to": to, **kwargs}
        return self._request("POST", "/v1/verify/send", json=payload)

    def check_otp(self, session_id: str, code: str) -> Dict[str, Any]:
        payload = {"session_id": session_id, "code": code}
        return self._request("POST", "/v1/verify/check", json=payload)

    def get_balance(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/billing/balance")

    def list_packs(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/billing/packs")

    def analytics(self, days: int = 30) -> Dict[str, Any]:
        return self._request("GET", f"/v1/analytics?days={days}")

    def list_messages(self, limit: int = 50) -> Dict[str, Any]:
        return self._request("GET", f"/v1/messages?limit={limit}")

    def create_api_key(self, **kwargs: Any) -> Dict[str, Any]:
        return self._request("POST", "/v1/api-keys", json=kwargs)

    def create_optout(self, phone: str) -> Dict[str, Any]:
        return self._request("POST", "/v1/optouts", json={"phone": phone})

    def list_payment_methods(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/billing/payment-methods")

    def create_topup(
        self,
        amount_eur: Optional[float] = None,
        amount_mad: Optional[float] = None,
        payment_method: str = "stripe",
        pack_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"payment_method": payment_method}
        if amount_eur is not None:
            payload["amount_eur"] = amount_eur
        if amount_mad is not None:
            payload["amount_mad"] = amount_mad
        if pack_id is not None:
            payload["pack_id"] = pack_id
        return self._request("POST", "/v1/billing/topups", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            timeout=20,
            **kwargs,
        )
        data = response.json()
        if response.status_code >= 400:
            error_msg = data.get("error", {}).get("message", f"EnvoiSMS API error: status {response.status_code}")
            raise RuntimeError(error_msg)
        return data
