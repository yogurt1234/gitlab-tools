# tests/conftest.py
import sys
from pathlib import Path

# ── BEFORE ──
# PROJECT_ROOT = Path(__file__).parent.resolve()
# sys.path.insert(0, str(PROJECT_ROOT))

# ── AFTER ──
# tests/ の親ディレクトリをプロジェクトルートとして sys.path に追加
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
