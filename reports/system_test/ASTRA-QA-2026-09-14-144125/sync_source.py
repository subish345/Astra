from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[3]
run=Path(__file__).resolve().parent
for folder in ['core','tests','apps','streaming']:
 for path in (root/folder).rglob('*.py'):
  dest=run/'workspace'/path.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
