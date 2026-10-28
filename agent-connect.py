"""Connect an Agent using a user-approved Coders link; Python standard library only."""

import argparse
import json
import os
import secrets
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def post(url, body):
    request = Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def connect(link, name="Agent"):
    url = urlsplit(link)
    if (
        url.scheme != "https"
        or url.netloc != "core-v2.coders.kr"
        or url.query
        or url.fragment
        or not url.path.startswith("/agent/connect/")
        or len(url.path.split("/")) != 4
    ):
        raise ValueError("Use the Coders Agent connection link copied from the Coders chip.")
    request = post(link + "/requests", {"name": name})
    origin = "https://core-v2.coders.kr"
    for key in ("approval_url", "poll_url"):
        target = urlsplit(request[key])
        if target.scheme + "://" + target.netloc != origin or not target.path.startswith(
            "/agent/requests/"
        ):
            raise ValueError("Invalid Coders approval response")
    print("사용자 승인: " + request["approval_url"], flush=True)
    print("확인 코드: " + request["verification_code"], flush=True)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        result = post(request["poll_url"], {"device_code": request["device_code"]})
        if result["status"] == "approved":
            directory = Path.home() / ".config" / "coders" / "agents"
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = directory / (secrets.token_hex(12) + ".json")
            # No token in terminal output, command arguments or public URLs.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as output:
                json.dump(result, output)
            print("연결 완료. 인증 파일: " + str(path), flush=True)
            print("만료 시각 (Unix): " + str(result["expires_at"]), flush=True)
            return path
        time.sleep(max(3, request.get("interval", 3)))
    raise TimeoutError("Approval expired. Create a new request.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("link")
    parser.add_argument("--name", default="Agent")
    args = parser.parse_args()
    try:
        connect(args.link, args.name)
    except HTTPError as error:
        raise SystemExit(
            f"연결 실패 (HTTP {error.code}). 승인을 거절했거나 연결이 만료되었을 수 있습니다."
        ) from None
    except (URLError, ValueError, TimeoutError) as error:
        raise SystemExit(str(error)) from None
