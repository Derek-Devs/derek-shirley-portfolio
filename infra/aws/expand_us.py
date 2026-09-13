"""Deploy the reviewed U.S. expansion without changing quotas, budgets, or the lease."""
import argparse
import hashlib
import json
from pathlib import Path
from manage import ROOT,session_for,inspect,seed_files,encoded

PACKAGE=ROOT/'.airport-data/aws-package'


def main():
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['runtime','activate-model','collect','verify'])
    p.add_argument('--profile',required=True); p.add_argument('--account-id',required=True)
    p.add_argument('--stack',default='portfolio-airport-weather'); args=p.parse_args()
    session=session_for(args); out=inspect(session,args)
    cf=session.client('cloudformation'); s3=session.client('s3'); lam=session.client('lambda')
    bucket=out['Bucket']; owner={'ExpectedBucketOwner':args.account_id}
    def get(key,cap=16*1024*1024):
        result=s3.get_object(Bucket=bucket,Key=key,**owner)
        if result['ContentLength']>cap: result['Body'].close(); raise ValueError('Stored object exceeds reviewed cap')
        with result['Body'] as body: raw=body.read(cap+1)
        if len(raw)>cap: raise ValueError('Stored object exceeds cap')
        return raw,result['ETag']
    if args.command=='runtime':
        receipt=json.loads((PACKAGE/'build-receipt.json').read_text())
        image=receipt.get('imageUri','')
        prefix=args.account_id+'.dkr.ecr.us-east-2.amazonaws.com/portfolio-airport-weather@sha256:'
        if receipt.get('buildStatus')!='SUCCEEDED' or not image.startswith(prefix): raise ValueError('Reviewed immutable image is not ready')
        stack=cf.describe_stacks(StackName=args.stack)['Stacks'][0]
        before={p['ParameterKey']:p['ParameterValue'] for p in stack['Parameters']}
        review={'oldParameters':before,'newImage':image,'limitsUnchanged':True,'leaseUnchanged':True}
        (PACKAGE/'v3-runtime-review.json').write_bytes(encoded(review))
        if before['ImageUri']==image: print('{"status":"runtime-already-current"}'); return
        parameters=[{'ParameterKey':key,**({'ParameterValue':image} if key=='ImageUri' else {'UsePreviousValue':True})} for key in before]
        response=cf.update_stack(StackName=args.stack,UsePreviousTemplate=True,Parameters=parameters,Capabilities=['CAPABILITY_IAM'])
        print(json.dumps({'status':'updating-runtime','stackId':response['StackId']})); return
    if args.command=='activate-model':
        files=seed_files()
        model=json.loads(files['active/model.json'])
        if model['version']!='airport-v3-us-local-expansion' or len(model['protocol']['airports'])!=100: raise ValueError('Unexpected expansion artifact')
        old_model,model_etag=get('active/model.json'); old_eval,eval_etag=get('active/evaluation.json')
        from guard import validate_pair
        validate_pair(json.loads(old_model),json.loads(old_eval),old_model)
        index_raw,index_etag=get('history/index.json'); old_index=json.loads(index_raw)
        new_index=json.loads(files['history/index.json'])
        if old_index['lastEvaluatedMonth']>'2026-06' or not set(old_index['months']).issubset(new_index['months']):
            raise ValueError('Preserve newer cloud history and evaluation frontier before migrating')
        stack=cf.describe_stacks(StackName=args.stack)['Stacks'][0]
        deployed={x['ParameterKey']:x['ParameterValue'] for x in stack['Parameters']}
        receipt=json.loads((PACKAGE/'build-receipt.json').read_text())
        if deployed['ImageUri']!=receipt['imageUri']: raise ValueError('Install expanded runtime first')
        for name,raw in [('model',old_model),('evaluation',old_eval),('history-index',index_raw)]:
            path=PACKAGE/f'v3-previous-{name}.json'
            if not path.exists(): path.write_bytes(raw)
        if old_model==files['active/model.json'] and old_eval==files['active/evaluation.json']:
            print('{"status":"model-already-active"}'); return
        selected={k:v for k,v in files.items() if k.startswith('history/') and k!='history/index.json'}
        for key,body in selected.items():
            s3.put_object(Bucket=bucket,Key=key,Body=body,ServerSideEncryption='AES256',**owner)
        new_index['lastEvaluatedMonth']=old_index['lastEvaluatedMonth']
        if 'lastAttempt' in old_index: new_index['lastAttempt']=old_index['lastAttempt']
        s3.put_object(Bucket=bucket,Key='history/index.json',Body=encoded(new_index),ServerSideEncryption='AES256',IfMatch=index_etag,**owner)
        # The collector checks both hashes; a partial switch cannot publish mismatched evidence.
        for key,etag in [('active/evaluation.json',eval_etag),('active/model.json',model_etag)]:
            s3.put_object(Bucket=bucket,Key=key,Body=files[key],ContentType='application/json',ServerSideEncryption='AES256',IfMatch=etag,**owner)
        review={'version':model['version'],'targetAirports':100,'uploadBytes':sum(map(len,selected.values())),
                'modelSha256':hashlib.sha256(files['active/model.json']).hexdigest(),'frontier':new_index['lastEvaluatedMonth']}
        (PACKAGE/'v3-model-activation.json').write_bytes(encoded(review)); print(json.dumps(review)); return
    if args.command=='collect':
        response=lam.invoke(FunctionName=args.stack+'-collector',InvocationType='RequestResponse',Payload=encoded({'job':'collector'}))
        with response['Payload'] as payload: result=payload.read(65537)
        if response.get('FunctionError'): raise RuntimeError(result.decode())
        (PACKAGE/'v3-collection.json').write_bytes(result); print(result.decode()); return
    latest,_=get('public/latest.json'); summary=json.loads(latest)
    risk_raw,_=get('public/'+summary['dataPrefix']+'/risk.json'); risk=json.loads(risk_raw)
    evidence_raw,_=get('public/'+summary['dataPrefix']+'/evaluation.json'); evidence=json.loads(evidence_raw)
    if risk['version']!='airport-v3-us-local-expansion' or evidence['version']!=risk['version'] or risk['generatedAt']!=summary['generatedAt']:
        raise ValueError('Expanded snapshot is not published yet')
    local_evidence=(ROOT/'public/data/airport-weather/evaluation.json').read_bytes()
    if hashlib.sha256(evidence_raw).digest()!=hashlib.sha256(local_evidence).digest(): raise ValueError('Cloud evidence differs from reviewed local evidence')
    result={'version':risk['version'],'generatedAt':risk['generatedAt'],'airportEntries':len(risk['airports']),
            'coverage':evidence['coverageSummary'],'currentAvailableSlices':sum(v['status']=='available' for a in risk['airports'].values() for d in a['directions'].values() for v in d.values())}
    (PACKAGE/'v3-cloud-verification.json').write_bytes(encoded(result)); print(json.dumps(result))
    # Mirror genuine cloud retrieval timestamps into the local fallback without provider calls.
    snapshot,_=get('state/latest.json')
    from sys import path
    path.insert(0,str(ROOT/'tools'))
    import airport_weather as weather
    weather.atomic_json(weather.STATE/'latest.json',json.loads(snapshot)); weather.publish(json.loads(snapshot))


if __name__=='__main__': main()
