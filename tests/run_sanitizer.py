from pathlib import Path
import subprocess
import sys

fixtures = Path(__file__).with_name("fixtures")
paths = sorted(str(p) for p in fixtures.iterdir() if p.suffix != ".rgba")
subprocess.run([sys.argv[1], *paths], check=True)
