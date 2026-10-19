"""Schema-only fuzz evidence; no network and no generated-code execution."""
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from pydantic import ValidationError
from app.schemas.strategy_lab import StrategyLabRunRequest

OUT = Path(__file__).parent/'evidence/20260906-public/schema.json'
CASES = {
 'prompt': ['', 'R', 'RSI', 'RSIX', 'RSI X', 'Buy when RSI is below 35.', *['x'*n for n in [1999,2000,2001,10000]]],
 'initial_cash': ['',0,-1,-100000,1,.01,999999999999999999,'harf','abc','1e10','NaN','Infinity',' ','1,5','1.5'],
 'commission': ['',-1,0,.0005,.002,.005,.01,.1,1,10,'abc','NaN','Infinity'],
}
rows=[]
for field, values in CASES.items():
    for i,value in enumerate(values):
        payload={'prompt':'Simple RSI strategy','symbol':'THYAO','initial_cash':100000,'commission':.002}
        payload[field]=value
        row={'id':f'SCHEMA-{field}-{i}', 'target':'local Pydantic schema, no HTTP', 'utc':datetime.now(timezone.utc).isoformat(), 'field':field, 'input':value if field!='prompt' or len(value)<80 else {'length':len(value)}}
        try:
            result=StrategyLabRunRequest.model_validate(payload)
            row.update(accepted=True, normalized=getattr(result,field) if field!='prompt' else len(result.prompt))
        except ValidationError as error:
            row.update(accepted=False,errors=[{'loc':e['loc'],'type':e['type']} for e in error.errors()])
        rows.append(row)
OUT.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'cases':len(rows),'accepted':sum(r['accepted'] for r in rows),'rejected':sum(not r['accepted'] for r in rows)}))
