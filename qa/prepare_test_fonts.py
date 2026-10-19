"""Fetch the public UI's exact fonts for deterministic non-Ahem widget tests."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

out=Path(__file__).parent/'fixtures/fonts'
out.mkdir(parents=True,exist_ok=True)
records=[]
for name,digest in [('Inter','15b294b67f2f8bbc04d990023ef4aec66502b87dc9040d84abe5f896ccb693de'),('Geist','ae7ee8606ec4b58cb0126a2410f15da7eb0a255131917cf679f815b9b4585a06')]:
    url=f'https://fonts.gstatic.com/s/a/{digest}.ttf'
    body=urlopen(url,timeout=40).read()
    actual=hashlib.sha256(body).hexdigest()
    if actual!=digest: raise ValueError('Public font hash mismatch')
    (out/(name+'.ttf')).write_bytes(body)
    license_url=f'https://raw.githubusercontent.com/google/fonts/main/ofl/{name.lower()}/OFL.txt'
    license_body=urlopen(license_url,timeout=30).read()
    (out/(name+'-OFL.txt')).write_bytes(license_body)
    records.append({'name':name,'url':url,'sha256':actual,'license':license_url})
(out/'sources.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps(records))
