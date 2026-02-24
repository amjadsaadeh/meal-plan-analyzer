import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent)
print(f"ROOT CONFTEST LOADED: {_root}")
print(f"SYS.PATH before: {sys.path[:3]}")
if _root not in sys.path:
    sys.path.insert(0, _root)
print(f"SYS.PATH after: {sys.path[:3]}")
