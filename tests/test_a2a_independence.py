"""The verifier is only a trust boundary if it cannot see what the reviewer saw.

This inspects what a fresh verifier process ACTUALLY loads (sys.modules), not just explicit imports, because
package __init__ files can pull in modules silently."""

import pytest
pytest.importorskip("google.adk")


import json
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWER_SIDE = ("agents.advisor_agent", "agents.orchestrator", "agents.context_agent", "agents.planner_agent",
                 "agents.verifier_client", "api", "mcp_server", "mcp", "review.service", "review.agents", "review.rendering")


def _loaded_modules(entry: str):
    code = (
        "import sys, json, warnings; warnings.filterwarnings('ignore'); "
        f"import {entry}; print(json.dumps(sorted(sys.modules)))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-500:]
    return json.loads(out.stdout.splitlines()[-1])


def test_a2a_verifier_process_loads_no_reviewer_side_code():
    leaked = [m for m in _loaded_modules("a2a_verifier.app")
              if m == "mcp" or any(m == p or m.startswith(p + ".") for p in REVIEWER_SIDE)]
    assert not leaked, f"verifier process loaded reviewer-side modules: {leaked}"


def _local_sources(entry: str):
    """Source text of every repo-owned module the verifier process loaded."""
    code = (
        "import sys, json, warnings, pathlib; warnings.filterwarnings('ignore'); "
        f"import {entry}; root = pathlib.Path('.').resolve(); "
        "files = [m.__file__ for m in sys.modules.values() if getattr(m, '__file__', None) "
        "and pathlib.Path(m.__file__).resolve().is_relative_to(root) and '.venv' not in m.__file__]; "
        "print(json.dumps(files))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-500:]
    return {f: pathlib.Path(f).read_text() for f in json.loads(out.stdout.splitlines()[-1])}


def test_a2a_verifier_code_never_creates_a_model_client_or_reads_a_key():
    """ADK imports google.genai as a library, so its module name is always loaded. What matters is that none of
    OUR code the verifier runs builds a model client, defines an LLM agent, or reads an API key."""
    sources = _local_sources("a2a_verifier.app")
    assert any(f.endswith("a2a_verifier/app.py") for f in sources), "expected the verifier's own module to be loaded"
    forbidden = ("genai.Client", "LlmAgent", "GEMINI_API_KEY", "generate_content", "GOOGLE_GENAI_USE_VERTEXAI", "VERIFIER_URL")
    hits = {f: [t for t in forbidden if t in src] for f, src in sources.items()}
    hits = {f: t for f, t in hits.items() if t}
    assert not hits, f"verifier-side code touches a model or reviewer config: {hits}"


def test_lazy_agents_package_still_exposes_every_agent():
    import agents
    for name in agents.__all__:
        assert getattr(agents, name).__name__ == name
