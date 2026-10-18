import socket
import subprocess
import sys
import time
import pathlib
import httpx
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def _wait(url: str, tries: int = 100):
    for _ in range(tries):
        try:
            httpx.get(url, timeout=0.5); return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"service at {url} did not start")


@pytest.fixture(scope="session")
def a2a_verifier_url():
    """A real A2A verifier in its own process."""
    port = _free_port()
    import os
    env = {**os.environ, "A2A_PUBLIC_PORT": str(port), "PYTHONPATH": str(ROOT)}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "a2a_verifier.app:app", "--port", str(port), "--log-level", "warning"],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait(f"http://127.0.0.1:{port}/.well-known/agent-card.json")
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate(); proc.wait(timeout=10)


@pytest.fixture(scope="session")
def mcp_url():
    """A real MCP server (streamable HTTP) in its own process."""
    port = _free_port()
    env = {"MCP_PORT": str(port), "PATH": "/usr/bin:/bin"}
    proc = subprocess.Popen([sys.executable, "-m", "mcp_server.server"], cwd=ROOT, env={**env, "PYTHONPATH": str(ROOT)},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                httpx.post(f"http://127.0.0.1:{port}/mcp", json={}, timeout=0.5); break
            except Exception:
                time.sleep(0.1)
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate(); proc.wait(timeout=10)
