import os
import sys
import tempfile
from pathlib import Path

# Every test run gets its own data folder; set before tarjuman.config is imported.
os.environ["TARJUMAN_NO_ENV_FILE"] = "1"  # the developer's own .env must not change what is tested
os.environ["TARJUMAN_HOME"] = tempfile.mkdtemp(prefix="tarjuman-test-")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
