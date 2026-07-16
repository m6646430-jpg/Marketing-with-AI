"""Configuration and secret loading."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"


def load_env(name="OPENROUTER_API_KEY"):
    """Read a var from the environment, falling back to the repo's .env.

    Kept deliberately dumb -- no python-dotenv dependency, and it tolerates
    values containing characters that would break `source .env`.
    """
    if os.environ.get(name):
        return os.environ[name]

    env_file = ROOT / ".env"
    if env_file.is_file():
        pattern = re.compile(rf'\s*(?:export\s+)?{re.escape(name)}\s*=\s*["\']?([^"\'\s]+)')
        for line in env_file.read_text().splitlines():
            m = pattern.match(line)
            if m:
                return m.group(1)

    raise SystemExit(
        f"{name} not set.\n"
        f"Add it to {env_file} (see .env.example) or export it."
    )
