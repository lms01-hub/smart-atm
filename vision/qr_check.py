"""Read an ATM session QR code and verify it with the backend API."""

import argparse
import json
import re
import sys
import time
from typing import Any, Dict

import cv2
import requests


DEFAULT_API_BASE_URL = "http://210.114.17.158:8000/api/v1/atm/verify"
SESSION_ID_PATTERN = re.compile(r"^VP-\d{6}$")


def parse_session_id(raw_data: str) -> str:
    """Parse and validate a session ID from a QR JSON payload."""
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ValueError("QR data is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("QR JSON must be an object")

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("session_id is missing")

    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("session_id must match VP- followed by 6 digits")

    return session_id


def response_detail(response: requests.Response) -> str:
    """Return a short error message from an unsuccessful response."""
    try:
        body = response.json()
    except requests.exceptions.JSONDecodeError:
        return response.text.strip() or "empty response"

    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return json.dumps(body, ensure_ascii=False)


def verify_session(
    session_id: str,
    api_base_url: str,
    timeout: float,
) -> None:
    """Call the ATM verify endpoint and print its result."""
    url = f"{api_base_url.rstrip('/')}/{session_id}"
    print(f"[QR] {session_id}")

    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        print(f"[API ERROR] Connection failed: {exc}")
        return

    if response.status_code != 200:
        print(
            f"[API ERROR] HTTP {response.status_code}: "
            f"{response_detail(response)}"
        )
        return

    try:
        body: Dict[str, Any] = response.json()
    except requests.exceptions.JSONDecodeError:
        print("[API ERROR] Server returned invalid JSON")
        return

    if not isinstance(body, dict):
        print("[API ERROR] Unexpected response format")
        return

    data = body.get("data")
    if body.get("success") is not True or not isinstance(data, dict):
        print("[API ERROR] Unexpected response format")
        return

    print(f"[RISK] {data.get('risk_level', 'UNKNOWN')}")
    print(f"[SCORE] {data.get('risk_score', 'UNKNOWN')}")
    print(f"[ACTION] {data.get('atm_action', 'UNKNOWN')}")
    print(f"[SUMMARY] {data.get('summary', '')}")


def draw_qr_outline(frame: Any, points: Any) -> None:
    """Draw the detected QR boundary on the preview frame."""
    if points is None:
        return
    polygon = points.astype(int).reshape(-1, 2)
    cv2.polylines(frame, [polygon], True, (0, 255, 0), 2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan a session QR code and call the ATM verify API."
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="OpenCV camera index (default: 0)",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="ATM verify endpoint without the trailing session ID",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=5.0,
        help="Seconds a QR must be absent before it can be processed again (min: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="API request timeout in seconds (default: 5)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.cooldown < 3.0:
        print("[CONFIG ERROR] --cooldown must be at least 3 seconds")
        return 2
    if args.timeout <= 0:
        print("[CONFIG ERROR] --timeout must be greater than 0")
        return 2

    camera = cv2.VideoCapture(args.camera_index)
    if not camera.isOpened():
        print(f"[CAMERA ERROR] Could not open camera index {args.camera_index}")
        camera.release()
        return 1

    detector = cv2.QRCodeDetector()
    active_qr_data = None
    active_last_seen = 0.0
    duplicate_announced = False
    last_call_by_session: Dict[str, float] = {}
    consecutive_read_failures = 0

    print("[READY] Show a QR code to the camera. Press q to quit.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                consecutive_read_failures += 1
                if consecutive_read_failures == 1:
                    print("[CAMERA ERROR] Failed to read a frame")
                if consecutive_read_failures >= 30:
                    print("[CAMERA ERROR] Too many consecutive read failures")
                    return 1
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                continue

            consecutive_read_failures = 0
            raw_data, points, _ = detector.detectAndDecode(frame)
            now = time.monotonic()

            if raw_data:
                draw_qr_outline(frame, points)

                if raw_data == active_qr_data:
                    active_last_seen = now
                    if not duplicate_announced:
                        print("[SKIP] Same QR is still visible")
                        duplicate_announced = True
                else:
                    active_qr_data = raw_data
                    active_last_seen = now
                    duplicate_announced = False

                    try:
                        session_id = parse_session_id(raw_data)
                    except ValueError as exc:
                        print(f"[QR ERROR] {exc}")
                    else:
                        last_call = last_call_by_session.get(session_id)
                        if last_call is not None and now - last_call < args.cooldown:
                            remaining = args.cooldown - (now - last_call)
                            print(
                                f"[SKIP] {session_id} is in cooldown "
                                f"({remaining:.1f}s remaining)"
                            )
                        else:
                            last_call_by_session[session_id] = now
                            verify_session(
                                session_id,
                                args.api_base_url,
                                args.timeout,
                            )
            elif (
                active_qr_data is not None
                and now - active_last_seen >= args.cooldown
            ):
                active_qr_data = None
                duplicate_announced = False

            cv2.imshow("ATM QR Scanner", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print("[EXIT] QR scanner stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
