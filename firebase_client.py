import json
import time
import requests
import streamlit as st


def _check_and_load_secrets() -> str:
    try:
        all_keys = list(st.secrets.keys())
    except Exception as exc:
        st.error("❌ secrets.toml not found. Please create `.streamlit/secrets.toml` with your Firebase config.")
        st.stop()

    if "firebase" not in st.secrets:
        st.error("❌ `[firebase]` section missing from secrets.toml.")
        st.stop()

    cfg = st.secrets["firebase"]

    if "database_url" not in cfg:
        st.error("❌ `database_url` key missing from `[firebase]` section.")
        st.stop()

    db_url = cfg["database_url"].rstrip("/")

    if "YOUR-PROJECT" in db_url:
        st.error("❌ `database_url` still contains a placeholder. Replace it with your real Firebase URL.")
        st.stop()

    return db_url


class FirebaseClient:
    """Minimal Firebase Realtime Database client using the REST API."""

    def __init__(self):
        self.db_url = _check_and_load_secrets()
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _url(self, path: str) -> str:
        clean = path.strip("/")
        return f"{self.db_url}/{clean}.json"

    def _safe_request(self, method: str, path: str, data=None, retries: int = 3):
        url = self._url(path)

        for attempt in range(retries):
            try:
                if method == "GET":
                    resp = self._session.get(url, timeout=5)

                elif method == "PUT":
                    resp = self._session.put(url, data=json.dumps(data), timeout=5)

                elif method == "PATCH":
                    resp = self._session.patch(url, data=json.dumps(data), timeout=5)

                elif method == "DELETE":
                    resp = self._session.delete(url, timeout=5)
                    if resp.status_code == 429:
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    if resp.status_code not in (200, 204):
                        st.error(f"Firebase DELETE Error {resp.status_code}: {resp.text}")
                    return None

                else:
                    return None

                if resp.status_code == 200:
                    return resp.json()

                if resp.status_code == 429:
                    time.sleep(0.5 * (attempt + 1))
                    continue

                st.error(f"Firebase {method} Error {resp.status_code}: {resp.text}")
                return None

            except requests.exceptions.RequestException as exc:
                if attempt < retries - 1:
                    time.sleep(0.3)
                else:
                    st.error(f"Firebase network error: {exc}")
                continue

        return None

    def get(self, path: str):
        return self._safe_request("GET", path)

    def get_scalar(self, path: str):
        return self._safe_request("GET", path)

    def set(self, path: str, data):
        return self._safe_request("PUT", path, data)

    def update(self, path: str, data: dict):
        if not isinstance(data, dict):
            raise ValueError("update() requires a dict; use set() for scalars.")
        return self._safe_request("PATCH", path, data)

    def delete(self, path: str) -> None:
        self._safe_request("DELETE", path)

    def get_list(self, path: str) -> list:
        val = self.get(path)
        if val is None:
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            return list(val.values())
        return []
