"""Capture local test command results as QA artifacts, never application secrets."""
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'qa/evidence/20260906-public'
mode=sys.argv[1]
commands = ([('flutter-qa',['C:/flutter/bin/flutter.bat','test','test/production_demo_qa_test.dart'],'mobile')]
 if mode=='widgets' else [
 ('flutter-analyze',['C:/flutter/bin/flutter.bat','analyze'],'mobile'),
 ('flutter-test',['C:/flutter/bin/flutter.bat','test'],'mobile'),
 ('backend-pytest',[str(ROOT/'backend/.venv/Scripts/python.exe'),'-m','pytest','-p','no:cacheprovider'],'backend'),
 ('security-regressions',[str(ROOT/'backend/.venv/Scripts/python.exe'),'-m','pytest','qa/test_security_regressions.py','qa/test_market_regressions.py','--tb=short','-q','-p','no:cacheprovider'],'.')])
for name,cmd,cwd in commands:
    started=datetime.now(timezone.utc).isoformat(); start=time.monotonic()
    p=subprocess.run(cmd,cwd=ROOT/cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
    (OUT/(name+'.txt')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    row={'id':name,'target':'local','start_utc':started,'end_utc':datetime.now(timezone.utc).isoformat(),'duration_seconds':time.monotonic()-start,'exit_code':p.returncode,'evidence':name+'.txt'}
    (OUT/(name+'.json')).write_text(json.dumps(row,indent=2),encoding='utf-8')
    print(json.dumps(row),flush=True)
