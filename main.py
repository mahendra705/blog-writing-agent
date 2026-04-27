import sys
from pathlib import Path

# ``python main.py`` does not put the package's parent on ``sys.path`` by default.
# Insert the directory that *contains* the ``research_writing_agent`` package folder.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from research_writing_agent import run

out = run(
"""
Comparision of latest OpenAI GPT Models vs Anthropic Claude Models 
Note: Add some comparsion images and charts of the models.
"""
)
print(out.get("markdown_path"))
print(out["final"])
