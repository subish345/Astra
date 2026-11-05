"""Campaign subprocess recorder: preserves commands, outputs and exit status."""
import os, sys, subprocess, json, time, signal, shlex
from pathlib import Path
from datetime import datetime, timezone
run=Path(__file__).resolve().parent
label,timeout,*command=sys.argv[1:]
path=run/(label+'.log'); path.parent.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM=os.environ.get('QA_QT_PLATFORM','offscreen'),TMPDIR=str(run/'automated/tmp'),MPLCONFIGDIR=str(run/'automated/matplotlib'))
Path(env['TMPDIR']).mkdir(exist_ok=True,parents=True)
start=time.monotonic(); timestamp=datetime.now(timezone.utc).isoformat()
with path.open('w') as log:
    p=subprocess.Popen(command,cwd=run/'workspace',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try: code=p.wait(timeout=float(timeout))
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        code=124
entry={'label':label,'timestamp':timestamp,'command':command,'shell_command':shlex.join(command),'cwd':str(run/'workspace'),'environment_overrides':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','QT_QPA_PLATFORM','TMPDIR','MPLCONFIGDIR']},'timeout_seconds':float(timeout),'exit_code':code,'duration_seconds':round(time.monotonic()-start,3),'log':str(path.relative_to(run))}
with (run/'commands.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
print(json.dumps(entry));print(path.read_text(errors='replace')[-6000:])
sys.exit(0)
