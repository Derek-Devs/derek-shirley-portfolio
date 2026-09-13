"""Fill exactly three operational-history gaps; never feed these months to the v3 experiment."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import airport_prepare_v3 as prep
from airport_weather import atomic_json


def main():
    folder=ROOT/'.airport-data/model-v3/operational-history'
    prep.configure(folder)
    zones=json.loads((ROOT/'.airport-data/model-v3/timezones.json').read_text())
    months=['2025-10','2025-11','2025-12']
    inventory=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(lambda month:prep.prepare_month(month,zones),months):
            inventory.append({k:v for k,v in result.items() if k!='rows'})
            inventory[-1]['rows']=len(result['rows'])
            atomic_json(folder/'inventory.json',inventory)
            print(json.dumps({'month':result['month'],'windows':len(result['rows']),
                              'purpose':'future rolling candidates only; excluded from current experiment'}),flush=True)


if __name__=='__main__': main()
