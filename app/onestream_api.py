# app/onestream_api.py
import requests
import streamlit as st
from typing import Optional

class OneStreamClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.auth_token = None

    def login(self) -> bool:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/authentication/login",
                json={"username": self.username, "password": self.password}
            )
            if resp.status_code == 200:
                self.auth_token = resp.json().get("token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                return True
            else:
                st.error(f"Login failed: {resp.status_code}")
                return False
        except Exception as e:
            st.error(f"Connection error: {e}")
            return False

    def get_dimensions(self) -> Optional[list]:
        resp = self.session.get(f"{self.base_url}/api/dimensions")
        return resp.json() if resp.status_code == 200 else None

    def run_business_rule(self, rule_id: str) -> dict:
        resp = self.session.post(f"{self.base_url}/api/rules/{rule_id}/execute")
        return resp.json()