import json, shutil
from pathlib import Path

DATA_DIR = Path("/app/data")
UNDO_FILE = DATA_DIR / "undo.json"

def save_undo(target_file: Path, label: str, redirect_url: str):
    if target_file.exists():
        UNDO_FILE.write_text(json.dumps({
            "target": str(target_file),
            "label": label,
            "redirect": redirect_url,
            "content": target_file.read_text(encoding="utf-8")
        }, ensure_ascii=False), encoding="utf-8")

def get_undo() -> dict | None:
    return json.loads(UNDO_FILE.read_text(encoding="utf-8")) if UNDO_FILE.exists() else None

def apply_undo() -> str:
    data = get_undo()
    if not data: return "/"
    Path(data["target"]).write_text(data["content"], encoding="utf-8")
    UNDO_FILE.unlink(missing_ok=True)
    return data.get("redirect", "/")
