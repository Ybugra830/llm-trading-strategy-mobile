"""Read-only remote/public checks. Raw journals and asset bodies are never saved."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import urlopen
from qa_driver import OUT, ROOT, SSH, URL, clean, save, utc, secret_found

stamp=sys.argv[1] if len(sys.argv)>1 else 'check'
command="cd /opt/llm-trading-strategy-mobile && git rev-parse HEAD && git status --short && sha256sum backend/app/validators/security_validator.py && systemctl show llm-strategy nginx -p ActiveState -p SubState -p NRestarts -p ExecMainStartTimestamp -p MemoryCurrent && docker info --format '{{.ServerVersion}} CPUs={{.NCPU}} RAM={{.MemTotal}} containers={{.ContainersRunning}}' && docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' && ss -ltn && free -m && curl -fsS http://127.0.0.1:8000/health && curl -fsS http://127.0.0.1/health && curl -fsS http://127.0.0.1/api/v1/strategy-lab/capabilities"
p=subprocess.run(SSH+[command],capture_output=True,text=True,timeout=45)
source=ROOT/'backend/app/validators/security_validator.py'
local_hash=hashlib.sha256(source.read_bytes()).hexdigest()
save(stamp+'-azure.json',{'utc':utc(),'rc':p.returncode,'summary':clean(p.stdout),'local_validator_sha256':local_hash,'remote_validator_matches':local_hash in p.stdout})
endpoints=[]
for path in ['/', '/health','/api/v1/strategy-lab/capabilities','/main.dart.js','/flutter_bootstrap.js']:
    start=utc()
    try:
        with urlopen(URL+path,timeout=40) as response:
            raw=response.read(); body=raw.decode('utf-8',errors='replace')
            row={'id':stamp+path,'start_utc':start,'end_utc':utc(),'url':URL+path,'http_status':response.status,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'secret_found':secret_found(body),'library_marker_counts':{key:body.count(key) for key in ['NVIDIA_API_KEY','Authorization','Bearer','.env','localhost:8000','10.0.2.2']}}
            if path in ['/health','/api/v1/strategy-lab/capabilities']: row['json']=json.loads(body)
            endpoints.append(row)
    except Exception as exc: endpoints.append({'url':URL+path,'error_type':type(exc).__name__})
save(stamp+'-public.json',endpoints)
# Only allowlisted tokens extracted from the test time interval; no raw messages.
command="journalctl -u llm-strategy --since '2026-09-06 09:00:00 UTC' --no-pager -o short-iso; sudo -n awk '$1 == \"2026/09/06\" && $2 >= \"09:00:00\"' /var/log/nginx/error.log; sudo -n awk '$4 ~ /06\\/Sep\\/2026/ { split($4,t,\":\"); if (t[2]+0 >= 9) print }' /var/log/nginx/access.log; sudo -n journalctl -k --since '2026-09-06 09:00:00 UTC' --no-pager -o short-iso"
p=subprocess.run(SSH+[command],capture_output=True,text=True,timeout=40)
rows=[]
for line in p.stdout.splitlines():
    fields=dict(re.findall(r'\b(phase|attempt|symbol|ticker|yahoo_symbol|error_type|code_hash_prefix|code_hash|strategy_code_hash|duration_seconds|model|stage|error_code)=([A-Za-z0-9_./:-]+)',line))
    status=re.search(r'"(?:POST|GET) (/[^\s"]+) HTTP/[^"]+" (\d{3})',line)
    timestamp=re.match(r'(\d{4}-\d\d-\d\dT[^ ]+)',line)
    access_time=re.search(r'\[(06/Sep/2026:[^]]+)\]',line)
    signals=[key for key,pattern in {'oom':r'out of memory|oom-kill|killed process','traceback':r'Traceback \(most recent','timeout':r'timeout|timed out','provider_429':r'\b429\b','provider_error':r'NvidiaNimError','yahoo_empty':r'Yahoo Finance returned empty','yahoo_parse_error':r'JSONDecodeError|YFPricesMissingError','docker_error':r'Docker.*[Ee]rror|SandboxUnavailable','worker_crash':r'worker.*(crash|exited|killed)'}.items() if re.search(pattern,line,re.I)]
    if fields or status or signals:
        row={'utc':timestamp.group(1) if timestamp else None,'nginx_time':access_time.group(1) if access_time else None,**fields,'signals':signals}
        if status: row.update(endpoint=status.group(1),http_status=int(status.group(2)))
        rows.append(row)
save(stamp+'-log-summary.json',{'collected_utc':utc(),'since_utc':'2026-09-06T09:00:00Z','command_rc':p.returncode,'rows':rows,'note':'No raw journals stored; simultaneous events without request ID are not assigned by guess.'})
print(json.dumps({'stamp':stamp,'azure_rc':p.returncode,'validator_matches':local_hash in json.loads((OUT/(stamp+'-azure.json')).read_text())['summary'],'public':[(r['url'],r.get('http_status')) for r in endpoints],'secret_found':any(r.get('secret_found') for r in endpoints),'signals':[r for r in rows if r['signals']]}))
