"""Automated GitHub Secrets Sync for JobIt.

Encrypts and updates GitHub Repository Secrets directly via GitHub REST API (PyNaCl)
without requiring manual copying or pasting.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

import requests
from nacl import encoding, public

logger = logging.getLogger("jobit.secrets_sync")


def get_git_credential_token() -> Optional[str]:
    """Retrieves GitHub token from environment or macOS git credential helper."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("PAT_TOKEN")
    if token:
        return token

    try:
        import subprocess
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="url=https://github.com\n",
            text=True,
            capture_output=True,
            check=True
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        logger.debug(f"Could not read token from git credential helper: {e}")

    return None


def sync_github_secret(
    secret_name: str,
    secret_value: str,
    owner: str = "manavmate53-jpg",
    repo: str = "JobIt",
    token: Optional[str] = None
) -> bool:
    """Encrypts and pushes secret_value to GitHub Actions Repository Secrets."""
    auth_token = token or get_git_credential_token()
    if not auth_token:
        logger.warning("No GitHub token available to update repository secret.")
        return False

    headers = {
        "Authorization": f"token {auth_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # 1. Fetch Repo Public Key
        key_res = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key",
            headers=headers,
            timeout=10
        )
        if key_res.status_code != 200:
            logger.warning(f"Failed to fetch public key: {key_res.status_code} - {key_res.text}")
            return False

        key_data = key_res.json()
        public_key = key_data["key"]
        key_id = key_data["key_id"]

        # 2. Encrypt value with PyNaCl SealedBox
        public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key_obj)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

        # 3. PUT Secret to GitHub API
        payload = {
            "encrypted_value": encrypted_b64,
            "key_id": key_id
        }
        put_res = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}",
            headers=headers,
            json=payload,
            timeout=10
        )

        success = put_res.status_code in [201, 204]
        if success:
            logger.info(f"Successfully synced secret '{secret_name}' to GitHub Actions!")
        else:
            logger.warning(f"Failed to PUT secret '{secret_name}': {put_res.status_code} - {put_res.text}")
        return success

    except Exception as e:
        logger.error(f"Error syncing GitHub secret {secret_name}: {e}")
        return False

