import sys
from pathlib import Path

# Ensure the current directory is on sys.path.
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from __init__ import run

out = run(
"""
Comparision of latest OpenAI GPT Models vs Anthropic Claude Models 
Note: Add some comparsion images and charts of the models.
"""
)
print(out.get("markdown_path"))
print(out["final"])
