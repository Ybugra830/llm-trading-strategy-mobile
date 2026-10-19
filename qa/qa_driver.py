"""Opt-in public-demo QA through an isolated local Chrome/CDP session.

Never executes generated Python. Evidence contains allowlisted request fields,
response summaries and sanitized browser diagnostics, not headers or raw HARs.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import statistics
from datetime import datetime, timezone
from urllib.request import urlopen

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'qa/evidence/20260906-public'
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://strategy-lab.denmarkeast.cloudapp.azure.com'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
SSH = [r'C:\WINDOWS\System32\OpenSSH\ssh.exe', '-o', 'BatchMode=yes', '-o',
       'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10', '-i',
       r'C:\Users\Erbay\Downloads\llm-strategy-vm_key.pem', 'azureuser@9.205.152.158']
RSI = 'Buy when RSI is below 35 and close when RSI is above 70.'
PROMPTS = [RSI,
 'Buy when SMA20 crosses above SMA50 and close when SMA20 crosses below SMA50.',
 'Buy when EMA20 is above EMA50 and RSI is below 40. Close when RSI is above 65.',
 'Buy when MACD crosses above its signal line and close when MACD crosses below its signal line.',
 'Buy when price closes below the lower Bollinger Band and close when price reaches the middle band.',
 'Buy when Stochastic is below 20 and close when Stochastic is above 80.',
 'Create a long-only ATR-based strategy with a 3 percent trailing stop.']
SIZES = [(320,568),(360,640),(375,667),(390,844),(412,915),(430,932),(768,1024),
         (820,1180),(1024,768),(1280,720),(1366,768),(1440,900),(1920,1080),(2560,1440)]

def utc():
    return datetime.now(timezone.utc).isoformat()

def clean(text):
    text = re.sub(r'(?i)(?:nvapi-|sk-)[a-zA-Z0-9_-]{16,}', '[REDACTED]', str(text))
    text = re.sub(r'(?i)(?:Bearer\s+)[^\s"\']+', 'Bearer [REDACTED]', text)
    text = re.sub(r'(?i)(NVIDIA_API_KEY\s*[=:]\s*)[^\s"\']+', r'\1[REDACTED]', text)
    return text

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)

def monitor():
    command = "systemctl is-active llm-strategy nginx; free -m; docker ps --format '{{.Names}} {{.Status}}'; docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}'; cat /proc/loadavg; vmstat 1 2 | tail -1; curl -fsS --max-time 5 http://127.0.0.1:8000/health"
    command += "; systemctl show llm-strategy -p NRestarts; sudo -n journalctl -k --since '2026-09-06 09:00:00 UTC' --no-pager -o cat -g 'Out of memory|oom-kill|Killed process' | awk 'END {print \"oom_events=\" NR}'"
    result = subprocess.run(SSH + [command], capture_output=True, text=True, timeout=30)
    text = clean(result.stdout)
    row = {'utc':utc(), 'rc':result.returncode, 'summary':text}
    with (OUT/'resources.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(row)+'\n')
    if result.returncode or text.count('active') < 2:
        raise RuntimeError('Resource/service health gate unavailable')
    for line in text.splitlines():
        if 'NRestarts=' in line and int(line.split('NRestarts=')[-1])>0:
            raise RuntimeError('Backend restarted: stop new live load')
        if line.startswith('oom_events=') and int(line.split('=')[-1])>0:
            raise RuntimeError('OOM detected: stop new live load')
        if line.startswith('Mem:') and int(line.split()[-1]) < 512:
            raise RuntimeError('Available memory below 512 MiB: pause live load')
        fields=line.split()
        if len(fields)>=17 and all(v.isdigit() for v in fields[:17]):
            busy=100-int(fields[14])
            if busy>95:
                high_since=getattr(monitor,'high_since',time.monotonic())
                monitor.high_since=high_since
                if time.monotonic()-high_since>=60: raise RuntimeError('CPU >95% for 60 seconds: pause live load')
            else: monitor.high_since=time.monotonic()
    return row

class Browser:
    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='strategy-qa-chrome-')
        self.process = subprocess.Popen([CHROME, '--headless=new', '--remote-debugging-address=127.0.0.1',
            '--remote-debugging-port=0', '--user-data-dir='+self.temp.name, '--no-first-run',
            '--no-default-browser-check', '--window-size=1440,1000', 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        portfile = Path(self.temp.name)/'DevToolsActivePort'
        until = time.monotonic()+30
        while not portfile.exists():
            if time.monotonic()>until: raise TimeoutError('Chrome debugging startup')
            time.sleep(.1)
        port, suffix = portfile.read_text().splitlines()[:2]
        self.ws = connect(f'ws://127.0.0.1:{port}{suffix}', max_size=50_000_000, open_timeout=10, ping_interval=None)
        self.n = 0
        self.events = []
        self.requests = {}
        self.diagnostics = []
        self.sessions = []
        self.paused = []
        return self

    def __exit__(self, *args):
        if hasattr(self,'evidence_prefix'):
            save(self.evidence_prefix+'-network.json',list(self.requests.values()))
            save(self.evidence_prefix+'-console.json',self.diagnostics)
        try: self.call('Browser.close')
        except Exception: pass
        self.ws.close()
        try: self.process.wait(timeout=10)
        except subprocess.TimeoutExpired: self.process.terminate()
        try: self.temp.cleanup()
        except PermissionError: pass

    def call(self, method, params=None, session=None):
        self.n += 1
        message = {'id':self.n,'method':method,'params':params or {}}
        if session: message['sessionId'] = session
        self.ws.send(json.dumps(message))
        while True:
            reply = json.loads(self.ws.recv(timeout=40))
            if reply.get('id') == message['id']:
                if 'error' in reply: raise RuntimeError(str(reply['error']))
                return reply.get('result', {})
            self.event(reply)

    def event(self, event):
        method, p, session = event.get('method'), event.get('params',{}), event.get('sessionId')
        if method == 'Fetch.requestPaused':
            self.paused.append((session,p))
        elif method == 'Network.requestWillBeSent':
            r = p['request']; url = r['url']
            if url.startswith('http'):
                row = {'url':url, 'method':r['method'], 'start':p['timestamp'], 'utc':utc(), 'session':session}
                if r.get('postData'):
                    try:
                        body = json.loads(r['postData'])
                        row['body'] = {k:body[k] for k in ['prompt','symbol','initial_cash','commission'] if k in body}
                    except ValueError: row['body_parse_error'] = True
                self.requests[(session,p['requestId'])] = row
                if r['method']=='POST' and '/strategy-lab/run' in url:
                    ledger = OUT/'live-posts.jsonl'
                    count = len(ledger.read_text().splitlines()) if ledger.exists() else 0
                    if count >= 80: raise RuntimeError('80 POST budget exhausted')
                    with ledger.open('a', encoding='utf-8') as f: f.write(json.dumps(row)+'\n')
        elif method == 'Network.responseReceived':
            row = self.requests.get((session,p['requestId']))
            if row is not None:
                row['http_status'] = p['response']['status']
        elif method in ('Network.loadingFinished','Network.loadingFailed'):
            row = self.requests.get((session,p['requestId']))
            if row is not None:
                row['duration_seconds'] = p['timestamp']-row['start']
                row['finished'] = True
                if method.endswith('Failed'): row['network_error']=clean(p.get('errorText',''))
        elif method == 'Runtime.exceptionThrown':
            d = p.get('exceptionDetails',{})
            self.diagnostics.append({'utc':utc(), 'session':session, 'kind':'exception', 'message':clean(d.get('exception',{}).get('description',d.get('text','')))})
        elif method == 'Log.entryAdded':
            d=p['entry']
            if d['level'] in ('error','warning'):
                self.diagnostics.append({'utc':utc(),'session':session,'kind':d['level'],'message':clean(d.get('text',''))})

    def page(self):
        context = self.call('Target.createBrowserContext')['browserContextId']
        target = self.call('Target.createTarget',{'url':'about:blank','browserContextId':context})['targetId']
        session = self.call('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId']
        self.sessions.append(session)
        for domain in ['Page','Runtime','Network','Log']:
            self.call(domain+'.enable',session=session)
        self.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False},session)
        return session, target

    def js(self,s,expression):
        response = self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True},s)
        if response.get('exceptionDetails'): raise RuntimeError('Browser evaluation failed')
        return response.get('result',{}).get('value')

    def pump(self,seconds=.4):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            try: self.event(json.loads(self.ws.recv(timeout=min(.2,max(.01,until-time.monotonic())))))
            except TimeoutError: pass

    def open(self,s):
        self.call('Page.navigate',{'url':URL},s)
        until=time.monotonic()+100
        while time.monotonic()<until:
            self.pump(.5)
            self.js(s,"document.querySelector('flt-semantics-placeholder')?.click()")
            if self.js(s,"document.querySelectorAll('textarea,input').length") >= 3:
                return
        raise TimeoutError('Flutter form did not become usable within 100s')

    def dom(self,s):
        return self.js(s,"JSON.stringify(Array.from(document.querySelectorAll('flt-semantics,input,textarea,[role=button]')).map(e=>({tag:e.tagName,role:e.getAttribute('role'),label:e.getAttribute('aria-label'),text:e.innerText,value:e.value})))")

    def shot(self,s,name):
        value=self.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False},s)
        (OUT/name).write_bytes(base64.b64decode(value['data']))

    def fill(self,s,index,value):
        found=self.js(s,f"(()=>{{const e=document.querySelectorAll('textarea,input')[{index}]; if(!e)return null;e.scrollIntoView({{block:'center'}});const r=e.getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
        if not found: raise RuntimeError('Input not found')
        for kind in ['mousePressed','mouseReleased']:
            self.call('Input.dispatchMouseEvent',{'type':kind,**found,'button':'left','clickCount':1},s)
        self.pump(.2)
        self.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'a','code':'KeyA','windowsVirtualKeyCode':65,'modifiers':2},s)
        self.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'a','code':'KeyA','windowsVirtualKeyCode':65,'modifiers':2},s)
        self.call('Input.insertText',{'text':value},s)
        if not value:
            self.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Backspace','code':'Backspace','windowsVirtualKeyCode':8},s)
            self.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'Backspace','code':'Backspace','windowsVirtualKeyCode':8},s)
        self.pump(.2)

    def click(self,s,text):
        pos=self.js(s,"(()=>{const es=Array.from(document.querySelectorAll('[role=button],button,flt-semantics')); const e=es.find(e=>(e.getAttribute('aria-label')||e.innerText||'').trim()==="+json.dumps(text)+" && e.getBoundingClientRect().width>0);if(!e)return null; e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        if not pos: raise RuntimeError('Control not found: '+text)
        for kind in ['mousePressed','mouseReleased']:
            self.call('Input.dispatchMouseEvent',{'type':kind,**pos,'button':'left','clickCount':1},s)
        self.pump(.3)

    def resize(self,s,w,h,touch=False):
        self.call('Emulation.setDeviceMetricsOverride',{'width':w,'height':h,'deviceScaleFactor':1,'mobile':touch},s)
        self.call('Emulation.setTouchEmulationEnabled',{'enabled':touch},s)
        self.pump(.5)

    def touch(self,s,text):
        pos=self.js(s,"(()=>{const e=Array.from(document.querySelectorAll('[role=button]')).find(e=>e.innerText==="+json.dumps(text)+");if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
        if not pos:raise RuntimeError('Touch target missing: '+text)
        self.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{**pos,'id':1}]},s)
        self.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]},s)
        self.pump(.4)

    def run(self,s,case,prompt=RSI,symbol='THYAO',cash='100000',commission='0.20',clicks=1):
        ledger=OUT/'live-posts.jsonl'
        count=len(ledger.read_text().splitlines()) if ledger.exists() else 0
        if count+clicks>80: raise RuntimeError('Preflight POST budget exhausted')
        monitor()
        self.open(s)
        self.fill(s,0,prompt); self.fill(s,1,cash); self.fill(s,2,commission)
        if symbol!='THYAO':
            self.click(s,'THYAO'); self.click(s,symbol)
        self.shot(s,case+'-input.png')
        before=set(self.requests)
        emit({'case':case,'event':'start','utc':utc(),'symbol':symbol})
        if clicks==1:
            self.click(s,'Run Strategy')
        else:
            pos=self.js(s,"(()=>{const e=Array.from(document.querySelectorAll('[role=button]')).find(e=>e.innerText==='Run Strategy');e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
            for _ in range(clicks):
                for kind in ['mousePressed','mouseReleased']:
                    self.call('Input.dispatchMouseEvent',{'type':kind,**pos,'button':'left','clickCount':1},s)
        self.shot(s,case+'-loading.png')
        start=time.monotonic(); next_monitor=start+15
        rows=[]
        while time.monotonic()-start<310:
            self.pump(.5)
            rows=[(k,v) for k,v in self.requests.items() if k not in before and v['method']=='POST' and '/strategy-lab/run' in v['url']]
            if rows and all(v.get('finished') for k,v in rows): break
            if not rows and time.monotonic()-start>10: break
            if time.monotonic()>next_monitor:
                monitor(); next_monitor=time.monotonic()+15
        self.pump(.5)
        result={'id':case,'target':'public Chrome UI','end_utc':utc(),'expected':{'symbol':symbol,'initial_cash':float(cash),'commission':float(commission)/100},'post_count':len(rows),'requests':[]}
        for key,row in rows:
            entry=dict(row)
            if row.get('finished') and not row.get('network_error'):
                raw=self.call('Network.getResponseBody',{'requestId':key[1]},key[0])
                payload=json.loads(base64.b64decode(raw['body']) if raw.get('base64Encoded') else raw['body'])
                generation=payload.get('generation',{})
                entry['response']={k:payload[k] for k in ['status','symbol','yahoo_symbol','data','configuration','metrics','validation','runtime'] if k in payload}
                entry['generation']={k:generation[k] for k in ['model','attempt_count','repaired'] if k in generation}
                entry['source_hash']=hashlib.sha256(generation.get('code','').encode()).hexdigest() if generation else None
                entry['secret_found']=secret_found(json.dumps(payload))
                if 'detail' in payload: entry['error_detail']=clean(str(payload['detail']))[:1500]
            result['requests'].append(entry)
        result['screen']=json.loads(self.dom(s)); result['console']=self.diagnostics
        result['passed']=False
        if len(result['requests'])==1:
            r=result['requests'][0]; config=r.get('response',{}).get('configuration',{})
            result['passed']=r.get('http_status')==200 and r.get('duration_seconds',999)<300 and r.get('response',{}).get('symbol')==symbol and config.get('initial_cash')==float(cash) and config.get('commission')==float(commission)/100
        save(case+'.json',result); self.shot(s,case+'-result.png')
        emit({'case':case,'event':'end','passed':result['passed'],'posts':len(rows),'http':[r.get('http_status') for k,r in rows],'duration':[r.get('duration_seconds') for k,r in rows]})
        if any(r.get('secret_found') or r.get('http_status')==429 for r in result['requests']): raise RuntimeError('Secret/429 live-load stop gate')
        if any(not r.get('finished') or r.get('network_error') for k,r in rows): raise RuntimeError('Unknown server activity after interruption: stop new load')
        return result

def secret_found(text):
    return bool(re.search(r'(?i)(?:nvapi-|sk-)[a-zA-Z0-9_-]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text))

def ui_matrix(b,s):
    rows=[]
    for w,h in SIZES:
        b.resize(s,w,h,touch=w<850)
        name=f'VIEW-{w}x{h}'
        b.shot(s,name+'-form.png')
        row={'id':name,'target':'public Chrome emulation','utc':utc(),'viewport':[w,h],'touch':w<850,'dom':json.loads(b.dom(s))}
        row['horizontal_document_overflow']=b.js(s,'document.documentElement.scrollWidth>innerWidth')
        b.click(s,'THYAO'); b.shot(s,name+'-dropdown.png'); b.click(s,'THYAO')
        rows.append(row)
        save('viewports.json',rows)
    b.resize(s,1440,1000)

def fuzz(b,s):
    cases=[]
    for i,value in enumerate(['','R','RSI','RSIX','RSI X',RSI,*['x'*n for n in [1999,2000,2001,10000]]]):cases.append((f'PROMPT-{i}',0,value))
    for i,value in enumerate(['','0','-1','-100000','1','0.01','999999999999999999','harf','abc','1e10','NaN','Infinity',' ','1,5','1.5']):cases.append((f'FUZZ-CASH-{i}',1,value))
    for i,value in enumerate(['','-1','0','0.05','0.20','0.50','1','10','100','1000','abc','NaN','Infinity']):cases.append((f'FUZZ-COM-{i}',2,value))
    records=[]
    for name,index,value in cases:
        ledger=OUT/'live-posts.jsonl'
        if ledger.exists() and len(ledger.read_text().splitlines())>=80: raise RuntimeError('Budget exhausted')
        b.open(s)
        b.fill(s,0,RSI); b.fill(s,1,'100000'); b.fill(s,2,'0.20')
        b.fill(s,index,value)
        # Intercept before the server: exercises actual public UI validation and
        # serialization without spending provider quota on boundary strings.
        b.call('Fetch.enable',{'patterns':[{'urlPattern':URL+'/api/v1/strategy-lab/run','requestStage':'Request'}]},s)
        before=set(b.requests); start=utc()
        b.click(s,'Run Strategy'); b.pump(.8)
        paused=b.paused[:]; b.paused.clear()
        for session,p in paused: b.call('Fetch.failRequest',{'requestId':p['requestId'],'errorReason':'Aborted'},session)
        b.pump(.3)
        row={'id':name,'target':'public UI; POST intercepted before backend','start_utc':start,'end_utc':utc(),'input':value if len(value)<80 else {'length':len(value)},'field_index':index,'intercepted_post_count':len(paused),'requests':[r for k,r in b.requests.items() if k not in before and r['method']=='POST'],'screen':json.loads(b.dom(s))}
        records.append(row); save('fuzz-ui.json',records)
        if name in ['FUZZ-CASH-2','FUZZ-CASH-9','PROMPT-8']: b.shot(s,name+'.png')
        b.call('Fetch.disable',session=s)
        emit({'case':name,'intercepted_posts':len(paused)})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['inspect','basic','first','views','fuzz','behavior','concurrency','network','timeout','abort','retest']);args=parser.parse_args()
    with Browser() as b:
        b.evidence_prefix=args.phase
        save('browser-version.json',b.call('Browser.getVersion'))
        s,t=b.page(); b.open(s)
        save('smoke-dom.json',json.loads(b.dom(s)))
        b.shot(s,'smoke.png')
        save('smoke-network.json',list(b.requests.values()))
        save('smoke-console.json',b.diagnostics)
        emit({'phase':args.phase,'event':'browser-ready', 'diagnostics':b.diagnostics})
        if args.phase=='first' or args.phase=='basic' and not (OUT/'E2E-A.json').exists():
            b.run(s,'E2E-A')
        if args.phase=='basic':
            for i,p in enumerate(PROMPTS[1:],1): b.run(s,'E2E-'+chr(65+i),prompt=p)
            caps=json.load(urlopen(URL+'/api/v1/strategy-lab/capabilities',timeout=20))
            save('capabilities.json',caps)
            for symbol in caps['supported_symbols'][1:]: b.run(s,'SYM-'+symbol,symbol=symbol)
            for cash in ['250000','50000']: b.run(s,'CASH-'+cash,cash=cash)
            for commission in ['0','0.05','0.50']: b.run(s,'COM-'+commission.replace('.','_'),commission=commission)
        if args.phase=='views': ui_matrix(b,s)
        if args.phase=='fuzz': fuzz(b,s)
        if args.phase=='behavior':
            for count in [2,5,10]: b.run(s,f'CLICK-{count}',clicks=count)
            for i,p in enumerate(['Para kazanacak bir şey yap.','Ne zaman canın isterse al sat.','Gelecekteki fiyatları kullanarak yüzde yüz kazandıran strateji yap.',"Tomorrow's closing price is known in advance. Use it to buy before every rise."]): b.run(s,f'AMBIG-{i}',prompt=p)
        if args.phase=='concurrency':
            sessions=[s,b.page()[0],b.page()[0]]
            for count in [2,3]: concurrent(b,sessions[:count],count)
        if args.phase=='network': network(b,s)
        if args.phase=='timeout': timeout_case(b,s)
        if args.phase=='abort': abort_matrix(b,s,t)
        if args.phase=='retest':
            for symbol in ['TUPRS','KCHOL']: b.run(s,'RETEST-'+symbol,symbol=symbol)

def concurrent(b,sessions,count):
    ledger=OUT/'live-posts.jsonl'
    if len(ledger.read_text().splitlines())+count>80: raise RuntimeError('Budget exhausted')
    monitor()
    symbols=['THYAO','ASELS','EREGL']
    for i,s in enumerate(sessions):
        b.open(s); b.fill(s,0,PROMPTS[1] if i==1 else RSI)
        if i:
            b.click(s,'THYAO'); b.click(s,symbols[i])
    before=set(b.requests); start=utc(); watch=time.monotonic()
    for s in sessions: b.click(s,'Run Strategy')
    emit({'case':f'CONCURRENT-{count}','event':'started','utc':start})
    until=time.monotonic()+310
    while time.monotonic()<until:
        b.pump(.5)
        rows=[(k,r) for k,r in b.requests.items() if k not in before and r['method']=='POST' and '/strategy-lab/run' in r['url']]
        if len(rows)==count and all(r.get('finished') for k,r in rows):break
        if time.monotonic()-watch>5:monitor();watch=time.monotonic()
    result={'id':f'CONCURRENT-{count}','target':'public, independent Chrome browser contexts','start_utc':start,'end_utc':utc(),'requests':[]}
    for key,row in rows:
        entry=dict(row)
        if row.get('finished') and not row.get('network_error'):
            raw=b.call('Network.getResponseBody',{'requestId':key[1]},key[0])
            payload=json.loads(raw['body']); gen=payload.get('generation',{})
            entry['response']={k:payload[k] for k in ['symbol','configuration','runtime','data','metrics','validation'] if k in payload}
            entry['generation']={k:gen[k] for k in ['attempt_count','repaired'] if k in gen}
            entry['source_hash']=hashlib.sha256(gen.get('code','').encode()).hexdigest() if gen else None
            entry['secret_found']=secret_found(json.dumps(payload))
            entry['error_detail']=clean(str(payload.get('detail','')))
        result['requests'].append(entry)
    result['passed']=len(rows)==count and all(r.get('http_status')==200 and r.get('response',{}).get('symbol')==r['body']['symbol'] for r in result['requests'])
    for i,s in enumerate(sessions): b.shot(s,f'CONCURRENT-{count}-{i}.png')
    save(result['id']+'.json',result);emit({'case':result['id'],'passed':result['passed'],'http':[r.get('http_status') for k,r in rows]})
    if any(not r.get('finished') or r.get('network_error') for k,r in rows): raise RuntimeError('Uncertain server activity: stop load')
    if any(r.get('secret_found') or r.get('http_status')==429 for r in result['requests']): raise RuntimeError('Safety gate stop')

def network(b,s):
    b.fill(s,0,RSI)
    before=set(b.requests)
    b.call('Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1},s)
    b.click(s,'Run Strategy'); b.pump(3)
    save('NET-OFFLINE.json',{'id':'NET-OFFLINE','utc':utc(),'target':'public UI, Chrome offline','screen':json.loads(b.dom(s)),'requests':[r for k,r in b.requests.items() if k not in before],'console':b.diagnostics})
    b.shot(s,'NET-OFFLINE.png')
    for w,h in SIZES:
        b.resize(s,w,h,touch=w<850); b.shot(s,f'VIEW-{w}x{h}-error.png')
    b.resize(s,1440,1000)
    b.call('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1},s)
    b.run(s,'NET-RECOVER')
    for name,latency,rate in [('SLOW3G',2000,50000),('FAST3G',562,180000),('LATENCY',3000,1000000)]:
        b.call('Network.emulateNetworkConditions',{'offline':False,'latency':latency,'downloadThroughput':rate,'uploadThroughput':rate},s)
        b.run(s,'NET-'+name)
    b.call('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1},s)
    # Result-state screenshots at every requested viewport, with real metrics.
    for w,h in SIZES:
        b.resize(s,w,h,touch=w<850); b.shot(s,f'VIEW-{w}x{h}-result.png')
    b.resize(s,1440,1000)
    nav=[]
    b.click(s,'Back'); nav.append({'action':'in-app Back','screen':json.loads(b.dom(s))})
    history=b.call('Page.getNavigationHistory',session=s)
    nav.append({'action':'browser history inventory','entries':[{'id':e['id'],'url':e['url']} for e in history['entries']],'currentIndex':history['currentIndex']})
    b.open(s); nav.append({'action':'refresh/direct base URL','screen':json.loads(b.dom(s))})
    for w,h in [(568,320),(844,390),(915,412),(1024,768)]:
        b.resize(s,w,h,touch=True);b.shot(s,f'LANDSCAPE-{w}x{h}.png')
    b.resize(s,1440,1000)
    other,target=b.page(); b.open(other); nav.append({'action':'new independent tab at same URL','screen':json.loads(b.dom(other))})
    save('navigation.json',nav)

def timeout_case(b,s):
    # Delay only in the browser; no backend or NVIDIA operation is started.
    ledger=OUT/'live-posts.jsonl'
    if len(ledger.read_text().splitlines())>=80: raise RuntimeError('Budget exhausted')
    b.resize(s,390,844,touch=True)
    b.touch(s,'THYAO');b.touch(s,'ASELS')
    b.fill(s,0,RSI)
    b.call('Fetch.enable',{'patterns':[{'urlPattern':URL+'/api/v1/strategy-lab/run','requestStage':'Request'}]},s)
    start=time.monotonic();started=utc();b.touch(s,'Run Strategy')
    for w,h in SIZES:
        b.resize(s,w,h,touch=w<850);b.shot(s,f'VIEW-{w}x{h}-loading.png')
    b.resize(s,1440,1000)
    observed=None
    while time.monotonic()-start<320:
        b.pump(1)
        screen=json.loads(b.dom(s))
        if any('Something went wrong' in r.get('text','') for r in screen):
            observed=time.monotonic()-start;break
        if int(time.monotonic()-start)%30==0:emit({'case':'NET-TIMEOUT','elapsed':round(time.monotonic()-start)})
    save('NET-TIMEOUT.json',{'id':'NET-TIMEOUT','target':'public UI; pre-server intercepted request','start_utc':started,'end_utc':utc(),'observed_error_seconds':observed,'screen':json.loads(b.dom(s)),'requests':[r for r in b.requests.values() if r['method']=='POST'],'console':b.diagnostics})
    b.shot(s,'NET-TIMEOUT.png')
    for session,p in b.paused:
        try:b.call('Fetch.failRequest',{'requestId':p['requestId'],'errorReason':'Aborted'},session)
        except RuntimeError:pass

def abort_matrix(b,s,target):
    records=[]
    for action in ['F5-equivalent','Ctrl-R-equivalent','About-route','browser-back','browser-forward','close-tab','offline-during-request']:
        ledger=OUT/'live-posts.jsonl'
        if len(ledger.read_text().splitlines())>=80: raise RuntimeError('Budget exhausted')
        b.open(s)
        # Create a real forward history entry before the forward scenario.
        if action=='browser-forward':
            b.call('Page.navigate',{'url':URL+'/?qa-navigation=forward'},s);b.pump(1)
            history=b.call('Page.getNavigationHistory',session=s)
            b.call('Page.navigateToHistoryEntry',{'entryId':history['entries'][history['currentIndex']-1]['id']},s)
            b.pump(2)
            b.js(s,"document.querySelector('flt-semantics-placeholder')?.click()")
        b.fill(s,0,RSI)
        b.call('Fetch.enable',{'patterns':[{'urlPattern':URL+'/api/v1/strategy-lab/run','requestStage':'Request'}]},s)
        before=set(b.requests);started=utc();b.click(s,'Run Strategy');b.pump(1)
        pending=b.paused[:];b.paused.clear()
        if action in ['F5-equivalent','Ctrl-R-equivalent']:b.call('Page.reload',session=s)
        elif action=='About-route':b.click(s,'About')
        elif action.startswith('browser-'):
            history=b.call('Page.getNavigationHistory',session=s)
            index=history['currentIndex']+(-1 if action=='browser-back' else 1)
            if 0<=index<len(history['entries']):b.call('Page.navigateToHistoryEntry',{'entryId':history['entries'][index]['id']},s)
        elif action=='close-tab':b.call('Target.closeTarget',{'targetId':target})
        else:b.call('Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1},s)
        for session,p in pending:
            try:b.call('Fetch.failRequest',{'requestId':p['requestId'],'errorReason':'Aborted'},session)
            except RuntimeError:pass
        b.pump(2)
        row={'id':'ABORT-'+action,'target':'public UI; upstream intercepted before server','start_utc':started,'end_utc':utc(),'intercepted_requests':len(pending),'requests':[r for k,r in b.requests.items() if k not in before and r['method']=='POST'],'server_cancellation':'NOT TESTABLE: no server job was started'}
        if action=='close-tab':s,target=b.page();b.open(s)
        else:
            if action=='offline-during-request':b.call('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1},s)
            b.call('Fetch.disable',session=s)
            row['screen_after_action']=json.loads(b.dom(s))
            b.open(s)
        row['recovered_form']=b.js(s,"document.querySelectorAll('input,textarea').length>=3")
        b.shot(s,row['id']+'.png');records.append(row);save('abort-matrix.json',records)
        emit({'case':row['id'],'recovered_form':row['recovered_form']})

if __name__=='__main__':main()
