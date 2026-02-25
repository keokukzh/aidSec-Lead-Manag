"""OpenClaw remote agent runner for pulling and completing queue tasks.

Usage (example):
    python scripts/agent_runner.py --agent-id agent1
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class RunnerConfig:
    api_base_url: str
    global_api_key: str
    agent_id: str
    agent_api_key: str
    lease_seconds: int = 300
    heartbeat_interval_seconds: int = 60
    poll_interval_seconds: int = 10
    request_timeout_seconds: int = 30
    once: bool = False


class AgentRunner:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.stop_event = threading.Event()
        self.session = requests.Session()
        self.logger = logging.getLogger(f"agent_runner.{config.agent_id}")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.global_api_key}",
            "X-API-Key": self.config.agent_api_key,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.config.api_base_url.rstrip('/')}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.config.request_timeout_seconds)
        kwargs.setdefault("headers", self.headers)
        response = self.session.request(method=method, url=self._url(path), **kwargs)
        return response

    def pull_task(self) -> dict[str, Any] | None:
        response = self._request(
            "GET",
            "/agents/tasks/pull",
            params={
                "agent_id": self.config.agent_id,
                "lease_seconds": self.config.lease_seconds,
            },
        )
        if response.status_code == 401:
            raise RuntimeError("Unauthorized: check API_KEY / AGENT_API_KEYS configuration")
        if response.status_code == 403:
            raise RuntimeError(f"Forbidden for agent_id={self.config.agent_id}; check AGENT_API_KEYS mapping")

        response.raise_for_status()
        data = response.json()
        return data.get("task")

    def heartbeat(self, task_id: int, lease_token: str) -> None:
        response = self._request(
            "POST",
            f"/agents/tasks/{task_id}/heartbeat",
            params={
                "agent_id": self.config.agent_id,
                "lease_seconds": self.config.lease_seconds,
            },
            json={"lease_token": lease_token},
        )
        if response.status_code in {401, 403, 409}:
            self.logger.warning("Heartbeat rejected for task %s: %s", task_id, response.text)
            return
        response.raise_for_status()

    def complete(self, task_id: int, lease_token: str, success: bool, result: dict[str, Any] | None = None, error: str | None = None) -> None:
        payload: dict[str, Any] = {
            "success": success,
            "lease_token": lease_token,
        }
        if result is not None:
            payload["result"] = result
        if error is not None:
            payload["error"] = error

        response = self._request(
            "POST",
            f"/agents/tasks/{task_id}/complete",
            params={"agent_id": self.config.agent_id},
            json=payload,
        )
        response.raise_for_status()

    def _run_heartbeat_loop(self, task_id: int, lease_token: str, heartbeat_stop_event: threading.Event) -> None:
        while not heartbeat_stop_event.wait(self.config.heartbeat_interval_seconds):
            if self.stop_event.is_set():
                return
            try:
                self.heartbeat(task_id, lease_token)
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Heartbeat failed for task %s: %s", task_id, exc)

    def _execute_generate_draft_task(self, task: dict[str, Any]) -> tuple[bool, dict[str, Any] | None, str | None]:
        lead_id = task.get("lead_id")
        payload = task.get("payload") or {}
        if not lead_id:
            return False, None, "Task has no lead_id"

        email_type = payload.get("email_type", "erstkontakt")
        response = self._request(
            "POST",
            "/agents/outreach",
            json={
                "lead_id": lead_id,
                "email_type": email_type,
            },
        )

        if response.status_code >= 400:
            return False, None, f"Outreach generation failed: HTTP {response.status_code} {response.text}"

        data = response.json()
        if not data.get("success"):
            return False, None, f"Outreach generation unsuccessful: {data}"

        subject = data.get("betreff") or "Automatisch generiert"
        body = data.get("inhalt") or data.get("raw") or ""
        if not body:
            return False, None, "Outreach response did not contain email body"

        return True, {"betreff": subject, "inhalt": body}, None

    def execute_task(self, task: dict[str, Any]) -> tuple[bool, dict[str, Any] | None, str | None]:
        task_type = task.get("type")
        if task_type == "GENERATE_DRAFT":
            return self._execute_generate_draft_task(task)
        return False, None, f"Unsupported task type: {task_type}"

    def run_forever(self) -> None:
        self.logger.info("Agent runner started (agent_id=%s, api=%s)", self.config.agent_id, self.config.api_base_url)

        while not self.stop_event.is_set():
            try:
                task = self.pull_task()
                if not task:
                    if self.config.once:
                        self.logger.info("No task available in once mode. Exiting.")
                        return
                    time.sleep(self.config.poll_interval_seconds)
                    continue

                task_id = int(task["id"])
                lease_token = task.get("lease_token")
                if not lease_token:
                    self.logger.error("Task %s has no lease token; skipping", task_id)
                    if self.config.once:
                        return
                    time.sleep(1)
                    continue

                self.logger.info("Pulled task id=%s type=%s lead_id=%s", task_id, task.get("type"), task.get("lead_id"))

                heartbeat_stop_event = threading.Event()
                heartbeat_thread = threading.Thread(
                    target=self._run_heartbeat_loop,
                    args=(task_id, lease_token, heartbeat_stop_event),
                    daemon=True,
                    name=f"heartbeat-{task_id}",
                )
                heartbeat_thread.start()

                try:
                    success, result, error = self.execute_task(task)
                finally:
                    heartbeat_stop_event.set()
                    heartbeat_thread.join(timeout=2)

                try:
                    self.complete(task_id, lease_token, success=success, result=result, error=error)
                    if success:
                        self.logger.info("Completed task id=%s successfully", task_id)
                    else:
                        self.logger.warning("Completed task id=%s as failed: %s", task_id, error)
                except Exception as exc:
                    self.logger.exception("Failed to complete task id=%s: %s", task_id, exc)

                if self.config.once:
                    return

            except requests.HTTPError as exc:
                self.logger.error("HTTP error: %s", exc)
                if self.config.once:
                    raise
                time.sleep(max(5, self.config.poll_interval_seconds))
            except Exception as exc:  # pragma: no cover
                self.logger.exception("Runner cycle error: %s", exc)
                if self.config.once:
                    raise
                time.sleep(max(5, self.config.poll_interval_seconds))

    def stop(self) -> None:
        self.stop_event.set()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw queue agent runner")
    parser.add_argument("--api-base-url", default=os.getenv("AIDSEC_API_BASE_URL", "http://100.100.97.120:8000/api"))
    parser.add_argument("--global-api-key", default=os.getenv("AIDSEC_GLOBAL_API_KEY", ""))
    parser.add_argument("--agent-id", default=os.getenv("AIDSEC_AGENT_ID", ""))
    parser.add_argument("--agent-api-key", default=os.getenv("AIDSEC_AGENT_API_KEY", ""))
    parser.add_argument("--lease-seconds", type=int, default=int(os.getenv("AIDSEC_LEASE_SECONDS", "300")))
    parser.add_argument("--heartbeat-interval-seconds", type=int, default=int(os.getenv("AIDSEC_HEARTBEAT_INTERVAL_SECONDS", "60")))
    parser.add_argument("--poll-interval-seconds", type=int, default=int(os.getenv("AIDSEC_POLL_INTERVAL_SECONDS", "10")))
    parser.add_argument("--request-timeout-seconds", type=int, default=int(os.getenv("AIDSEC_REQUEST_TIMEOUT_SECONDS", "30")))
    parser.add_argument("--once", action="store_true", default=False)
    parser.add_argument("--log-level", default=os.getenv("AIDSEC_AGENT_LOG_LEVEL", "INFO"))
    return parser


def _validate_config(config: RunnerConfig) -> None:
    if not config.agent_id:
        raise ValueError("Missing agent_id (set --agent-id or AIDSEC_AGENT_ID)")
    if not config.global_api_key:
        raise ValueError("Missing global_api_key (set --global-api-key or AIDSEC_GLOBAL_API_KEY)")
    if not config.agent_api_key:
        raise ValueError("Missing agent_api_key (set --agent-api-key or AIDSEC_AGENT_API_KEY)")

    if config.heartbeat_interval_seconds >= config.lease_seconds:
        raise ValueError("heartbeat_interval_seconds must be lower than lease_seconds")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = RunnerConfig(
        api_base_url=args.api_base_url,
        global_api_key=args.global_api_key,
        agent_id=args.agent_id,
        agent_api_key=args.agent_api_key,
        lease_seconds=args.lease_seconds,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
        once=bool(args.once),
    )

    try:
        _validate_config(config)
    except ValueError as exc:
        logging.getLogger("agent_runner").error(str(exc))
        return 2

    runner = AgentRunner(config)

    def _handle_stop(signum: int, _frame: Any) -> None:
        logging.getLogger("agent_runner").info("Received signal %s, stopping runner...", signum)
        runner.stop()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    try:
        runner.run_forever()
    except Exception:
        logging.getLogger("agent_runner").exception("Runner terminated with error")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
