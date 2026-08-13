from __future__ import annotations
import json, random
from pathlib import Path
SEED=20260813
RNG=random.Random(SEED+71)
RELATIONS=[
 ('code','ZX'),('email','user'),('version','V'),('provider','Provider'),('owner','Owner'),
 ('status','STATE'),('time','TIME'),('location','Room'),('quantity','QTY'),('price','PRICE')
]

def val(rel,idx):
    if rel=='email': return f"clean{idx}@example.test"
    if rel=='time': return f"{8+(idx%10):02d}:{(idx*7)%60:02d}"
    if rel=='location': return f"Room {chr(65+idx%20)}{idx%9+1}"
    if rel=='quantity': return str(10+idx)
    if rel=='price': return str(50+idx*3)
    if rel=='provider': return f"Provider{idx}"
    if rel=='owner': return f"Owner{idx}"
    if rel=='status': return ['READY','ACTIVE','PAUSED','APPROVED'][idx%4]
    if rel=='version': return f"V{idx%17+1}"
    return f"ZX-{100+idx}"

def m(mid,text,day):
    return {'id':mid,'text':text,'timestamp':f"2026-07-{day:02d}T12:00:00+00:00"}

def answerable():
    out=[]
    for idx in range(1,81):
        rel,_=RELATIONS[(idx-1)%len(RELATIONS)]
        ent=f"CLEANADV-A-{idx:03d}"
        value=val(rel,idx)
        rid=f"ca{idx}-r"
        memories=[
          m(rid,f"The current {rel} for {ent} updated to {value}.",10+(idx%8)),
          m(f"ca{idx}-echo",f"What is the current {rel} for {ent}?",28),
          m(f"ca{idx}-agenda",f"The current {rel} for {ent} remains on the agenda only.",29),
          m(f"ca{idx}-review",f"Review of the current {rel} for {ent} is scheduled.",30),
          m(f"ca{idx}-wrongsubj",f"The current {rel} for CLEANADV-X-{idx:03d} is DECOY-{idx}.",31),
          m(f"ca{idx}-stale",f"The previous {rel} for {ent} was OLD-{idx}.",27),
          m(f"ca{idx}-noise1",f"The current color for CLEANADV-N-{idx:03d} updated to amber.",26),
          m(f"ca{idx}-noise2",f"The current budget for CLEANADV-N-{idx:03d} updated to {4000+idx}.",25),
        ]
        RNG.shuffle(memories)
        out.append({'id':f'cleanadv-answerable-{idx:03d}','category':'adversarial_answerable','query':f'What is the current {rel} for {ent}?','memories':memories,'relevant_memory_ids':[rid],'expected_answerable':True})
    return out

def no_evidence():
    out=[]
    cats=['agenda','review','question','no_value','wrong_subject','wrong_relation','stale_only','negative','inference','meta']
    for idx in range(1,41):
        rel,_=RELATIONS[(idx-1)%len(RELATIONS)]
        ent=f"CLEANADV-N-{idx:03d}"
        cat=cats[(idx-1)%len(cats)]
        if cat=='agenda': core=[f"The current {rel} for {ent} remains on the agenda only."]
        elif cat=='review': core=[f"Review of the current {rel} for {ent} is scheduled."]
        elif cat=='question': core=[f"Question about the current {rel} for {ent} remains open."]
        elif cat=='no_value': core=[f"The record contains no recorded value for the current {rel} of {ent}."]
        elif cat=='wrong_subject': core=[f"The current {rel} for CLEANADV-OTHER-{idx:03d} updated to DECOY-{idx}."]
        elif cat=='wrong_relation':
            other='provider' if rel!='provider' else 'code'; core=[f"The current {other} for {ent} updated to DECOY-{idx}."]
        elif cat=='stale_only': core=[f"The previous {rel} for {ent} was OLD-{idx}.",f"The historical {rel} for {ent} was ARCHIVE-{idx}."]
        elif cat=='negative': core=[f"The current {rel} for {ent} is not DECOY-{idx}."]
        elif cat=='inference': core=[f"The current {rel} for {ent} is probably GUESS-{idx}."]
        else: core=[f"We discussed the current {rel} for {ent} during planning."]
        memories=[m(f"cn{idx}-core{k}",t,20+k) for k,t in enumerate(core)]
        memories += [
          m(f"cn{idx}-n1",f"The current color for CLEANADV-O-{idx:03d} updated to blue.",31),
          m(f"cn{idx}-n2",f"The current budget for CLEANADV-O-{idx:03d} updated to {5000+idx}.",30),
          m(f"cn{idx}-n3",f"The current owner for CLEANADV-O-{idx:03d} updated to Alex.",29),
          m(f"cn{idx}-n4",f"The current status for CLEANADV-O-{idx:03d} updated to READY.",28),
          m(f"cn{idx}-n5",f"The current provider for CLEANADV-O-{idx:03d} updated to Northwind.",27),
          m(f"cn{idx}-n6",f"The current code for CLEANADV-O-{idx:03d} updated to ZX-999.",26),
        ]
        RNG.shuffle(memories)
        out.append({'id':f'cleanadv-noevidence-{idx:03d}','category':cat,'query':f'What is the current {rel} for {ent}?','memories':memories,'relevant_memory_ids':[],'expected_answerable':False})
    return out

def main():
    cases=answerable()+no_evidence()
    assert len(cases)==120 and sum(bool(c['relevant_memory_ids']) for c in cases)==80
    assert len({c['id'] for c in cases})==120
    p=Path(__file__).with_name('adversarial-clean-v1.json')
    p.write_text(json.dumps(cases,indent=2,sort_keys=True)+'\n')
    print(p)
if __name__=='__main__':main()
