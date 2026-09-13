"""Portable numeric tree/linear inference. The live path imports no scientific packages."""
import math


def logit_one(head,vector):
    if 'trees' not in head:
        if len(head['coef'])!=len(vector): raise ValueError('Head dimension mismatch')
        return head['intercept']+sum(a*b for a,b in zip(vector,head['coef']))
    value=head['intercept']
    for tree in head['trees']:
        index=0
        for _ in range(len(tree)):
            feature,threshold,left,right,leaf=tree[index]
            if feature==-1:
                value+=leaf; break
            index=left if vector[feature]<=threshold else right
        else: raise ValueError('Invalid tree cycle')
    return value


def logit_many(head,x):
    import numpy as np
    if '_native' in head: return head['_native'].decision_function(x)
    if 'trees' not in head: return x@np.array(head['coef'])+head['intercept']
    result=np.full(len(x),head['intercept'],dtype=float)
    for tree in head['trees']:
        nodes=np.array(tree); index=np.zeros(len(x),dtype=int)
        for _ in range(len(tree)):
            active=nodes[index,0]>=0
            if not active.any(): break
            rows=np.flatnonzero(active); at=index[active]; field=nodes[at,0].astype(int)
            index[active]=np.where(x[rows,field]<=nodes[at,1],nodes[at,2],nodes[at,3]).astype(int)
        else: raise ValueError('Invalid tree cycle')
        result+=nodes[index,4]
    return result


def calibrated_one(head,vector,raw_vector):
    raw=logit_one(head,vector); cal=head['calibration']
    extra=raw_vector[:cal.get('airportCount',0)]
    value=cal['intercept']+raw*cal['coef'][0]+sum(a*b for a,b in zip(extra,cal['coef'][1:]))
    return 1/(1+math.exp(-max(-35,min(35,value))))


def predict_batch(model,x):
    import numpy as np
    scaled=(x-np.array(model['mean']))/np.array(model['scale']); q={}
    for name,head in model['heads'].items():
        raw=logit_many(head,scaled); cal=head['calibration']
        value=raw*cal['coef'][0]+cal['intercept']
        if cal.get('airportCount'): value+=x[:,:cal['airportCount']]@np.array(cal['coef'][1:])
        q[name]=1/(1+np.exp(-np.clip(value,-35,35)))
    cancel=q['cancelled']; divert=(1-cancel)*q.get('diverted',np.zeros(len(x)))
    delayed=(1-cancel-divert)*q['delayed']
    return {'cancelled':cancel,'diverted':divert,'delayed':delayed,'disruption':cancel+divert+delayed,'onTime':1-cancel-divert-delayed}


def interval_offsets(spec,probability):
    if isinstance(spec,(float,int)): return (-spec,spec)
    key='0' if probability<.25 else '1' if probability<.5 else '2'
    return spec['bins'].get(key,spec['global'])


def serializable(value):
    if isinstance(value,dict): return {k:serializable(v) for k,v in value.items() if not k.startswith('_')}
    if isinstance(value,list): return [serializable(v) for v in value]
    return value
