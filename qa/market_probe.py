"""Read-only remote market-provider diagnostic, no LLM or strategy execution."""
import json
import subprocess
from qa_driver import SSH, save, utc

program = '''
import json
from app.market.yahoo_provider import YahooFinanceProvider
from app.market.ohlcv_cleaner import clean_ohlcv
rows=[]
for symbol in ['TUPRS.IS','KCHOL.IS']:
    result={'symbol':symbol}
    try:
        data=YahooFinanceProvider().download_daily(symbol)
        result.update(rows=len(data), columns=list(data.columns))
        try:
            clean_ohlcv(data)
            result['cleaner']='accepted'
        except Exception as exc:
            result['cleaner']=type(exc).__name__
        for left,right in [('High','Open'),('High','Close'),('Open','Low'),('Close','Low'),('High','Low')]:
            difference=data[left]-data[right]
            result[left+'-below-'+right]={'count':int((difference<0).sum()),'min_difference':float(difference.min())}
        result['nonpositive_price_rows']=int((data[['Open','High','Low','Close']]<=0).any(axis=1).sum())
        result['negative_volume_rows']=int((data['Volume']<0).sum())
    except Exception as exc: result['error_type']=type(exc).__name__
    rows.append(result)
print(json.dumps(rows))
'''
start=utc()
p=subprocess.run(SSH+['cd /opt/llm-trading-strategy-mobile/backend && .venv/bin/python -'],input=program,capture_output=True,text=True,timeout=60)
rows=[]
for line in p.stdout.splitlines():
    try:
        candidate=json.loads(line)
        if isinstance(candidate,list): rows=candidate
    except ValueError:pass
save('market-diagnostic.json',{'id':'MARKET-DIAG','target':'Azure original provider and cleaner; no strategy','start_utc':start,'end_utc':utc(),'rc':p.returncode,'results':rows})
print(json.dumps(rows))
