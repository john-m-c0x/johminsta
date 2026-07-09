"""refresh_ig_token.py - extend the instagram long-lived token before it expires

instagram long-lived tokens last 60 days and can only be refreshed (not
regenerated) via this endpoint, and only once they're at least 24h old. run
this before posting so a scheduled workflow never goes stale. when GH_PAT is
set, the refreshed token is also written back to the repo secret so future
runs pick it up.
"""

import base64
import os

import requests
from nacl import encoding, public


def _refresh(token: str) -> dict:
    resp = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"refresh failed: {data}")
    return data


def _encrypt_for_github(public_key_b64: str, secret_value: str) -> str:
    key        = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    sealed_box = public.SealedBox(key)
    encrypted  = sealed_box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def _update_github_secret(repo: str, pat: str, name: str, value: str) -> None:
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept":        "application/vnd.github+json",
    }
    key_resp = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers,
    )
    key_resp.raise_for_status()
    key_data = key_resp.json()

    put_resp = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{name}",
        headers=headers,
        json={
            "encrypted_value": _encrypt_for_github(key_data["key"], value),
            "key_id":          key_data["key_id"],
        },
    )
    put_resp.raise_for_status()


def main() -> None:
    token = os.environ["INSTAGRAM_ACCOUNT_TOKEN"]

    try:
        refreshed = _refresh(token)
        token = refreshed["access_token"]
        print(f"::add-mask::{token}")
        print(f"refreshed instagram token, expires in {refreshed['expires_in']}s")

        pat  = os.getenv("GH_PAT")
        repo = os.getenv("GITHUB_REPOSITORY")
        if pat and repo:
            _update_github_secret(repo, pat, "INSTAGRAM_ACCOUNT_TOKEN", token)
            print("persisted refreshed token to the INSTAGRAM_ACCOUNT_TOKEN repo secret")
        else:
            print("GH_PAT not set - refreshed token only applied for this run, not persisted")
    except RuntimeError as e:
        print(f"::warning::instagram token refresh skipped - {e}")

    # make sure downstream steps see the (possibly refreshed) token either way
    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as f:
            f.write(f"INSTAGRAM_ACCOUNT_TOKEN={token}\n")


if __name__ == "__main__":
    main()
