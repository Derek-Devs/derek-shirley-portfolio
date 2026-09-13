"""Install a validated optional operations pair without replacing the weather model."""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
import time
import sys
from manage import ROOT,session_for,inspect,encoded
sys.path.insert(0,str(ROOT/'tools'))


def main():
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['review','install','runtime','verify'])
    p.add_argument('--profile',required=True); p.add_argument('--account-id',required=True)
    args=p.parse_args(); args.stack='portfolio-airport-weather'
    session=session_for(args); out=inspect(session,args); s3=session.client('s3')
    def read(key):
        r=s3.get_object(Bucket=out['Bucket'],Key=key,ExpectedBucketOwner=args.account_id)
        if r['ContentLength']>16*1024*1024: r['Body'].close(); raise ValueError('Read cap')
        with r['Body'] as body: return body.read(16*1024*1024+1)
    public=ROOT/'public/data/airport-weather'; folder=public/'operations'; work=ROOT/'.airport-data/operations-us-v1'
    release=json.loads((folder/'release.json').read_text()); version=release['version']
    if version!='airport-operations-us-v1': raise ValueError('Unreviewed operations version')
    for name in ('model.json','evaluation.json'):
        if read('active/'+name)!=(public/name).read_bytes(): raise ValueError('Current weather pair differs')
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=release['files'][name]: raise ValueError('Candidate hash differs')
    report=json.loads((public/'experiments/operations-us-v1.json').read_text())
    if report['defaultModel']!=release['defaultModel'] or report['validation']['savedModelScoresReproduced']!=2868:
        raise ValueError('Validated default decision missing')
    if any(hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()!=h for name,h in report['inputs']['code'].items()):
        raise ValueError('Frozen model code changed')
    raw_model=(folder/'model.json').read_bytes(); raw_evaluation=(folder/'evaluation.json').read_bytes()
    from guard import validate_pair,LIMITS
    validate_pair(json.loads(raw_model),json.loads(raw_evaluation),raw_model)
    control=session.client('dynamodb').get_item(TableName=out['ControlTable'],Key={'id':{'S':'control'}},ConsistentRead=True)['Item']
    if not control.get('enabled',{}).get('BOOL') or int(control.get('authorizedUntil',{}).get('N','0'))<=datetime.now(timezone.utc).timestamp():
        raise ValueError('Service is disabled or lease expired; this command cannot reactivate it')
    if args.command=='review':
        import handler
        seeds={'active/model.json':read('active/model.json'),'active/evaluation.json':read('active/evaluation.json'),
            'public/airports.json':read('public/airports.json'),'state/latest.json':read('state/latest.json'),
            f'active/operations/versions/{version}/model.json':raw_model,
            f'active/operations/versions/{version}/evaluation.json':raw_evaluation}
        catalog=json.loads(seeds['public/airports.json']); catalog['operationsRelease']=release
        seeds['public/airports.json']=encoded(catalog)
        class MemoryS3:
            def get_object(self,Bucket,Key):
                raw=seeds[Key]; return {'ContentLength':len(raw),'Body':io.BytesIO(raw)}
            def put_object(self,**kwargs): seeds[kwargs['Key']]=kwargs['Body']
        class Context:
            def get_remaining_time_in_millis(self): return max(0,120000-int((time.perf_counter()-started)*1000))
        started=time.perf_counter(); result=handler.collect(MemoryS3(),out['Bucket'],Context())
        snapshot=json.loads(seeds['state/latest.json']); manifest=json.loads(seeds['public/latest.json'])
        prefix='public/'+manifest['dataPrefix']+'/'
        risk=json.loads(seeds[prefix+'operations/risk.json'])
        proof={'status':'reviewed-not-installed','seconds':round(time.perf_counter()-started,3),'sources':snapshot['sources'],
            'liveAirportProbabilities':sum(any('probabilities' in v for d in a['directions'].values() for v in d.values()) for a in risk['airports'].values()),
            'publicBytes':sum(len(v) for k,v in seeds.items() if k.startswith(prefix)),
            'archiveBytes':len(gzip.compress(encoded(snapshot))), 'control':control,'release':release,'limits':LIMITS,
            'runtimeFiles':{str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'tools'/name for name in ['airport_weather.py','airport_predict.py','airport_faa_history.py','airport_faa_collect.py','airport_operations_score.py']]+[ROOT/'infra/aws/runtime/handler.py',ROOT/'infra/aws/runtime/guard.py',ROOT/'infra/aws/limits.json']}}
        if proof['publicBytes']>LIMITS['maximumPublicSnapshotBytes'] or proof['archiveBytes']>LIMITS['maximumCompressedArchiveBytes']:
            raise ValueError('Runtime storage cap')
        (work/'live-review.json').write_bytes(encoded(proof)); (work/'live-review-snapshot.json').write_bytes(encoded(snapshot))
        (work/'live-review-risk.json').write_bytes(encoded(risk))
        print(json.dumps({k:proof[k] for k in ['status','seconds','liveAirportProbabilities','publicBytes','archiveBytes','sources']})); return
    if args.command=='runtime':
        import re
        package=ROOT/'.airport-data/aws-package'; receipt=json.loads((package/'build-receipt.json').read_text())
        build=json.loads((package/'build-inputs.json').read_text()); image=receipt.get('imageUri','')
        if receipt.get('buildStatus')!='SUCCEEDED' or receipt.get('sourceSha256')!=build['sourceSha256']:
            raise ValueError('Successful immutable build required')
        if not re.fullmatch(args.account_id+r'\.dkr\.ecr\.us-east-2\.amazonaws\.com/portfolio-airport-weather@sha256:[a-f0-9]{64}',image):
            raise ValueError('Wrong runtime image')
        if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h for name,h in build['files'].items()):
            raise ValueError('Build inputs changed')
        cf=session.client('cloudformation'); stack=cf.describe_stacks(StackName=args.stack)['Stacks'][0]
        old=cf.get_template(StackName=args.stack,TemplateStage='Original')['TemplateBody']
        if isinstance(old,str): old=json.loads(old)
        before=json.loads(json.dumps(old)); edge=old['Resources']['PathGuard']['Properties']['FunctionCode']
        pattern=r'evaluation\.json|stations'; replacement=r'evaluation\.json|operations\/(?:risk|evaluation|release)\.json|stations'
        if pattern not in edge and replacement not in edge: raise ValueError('Unrecognized live path guard')
        revised=edge.replace(pattern,replacement)
        old['Resources']['PathGuard']['Properties']['FunctionCode']=revised
        parameters={p['ParameterKey']:p['ParameterValue'] for p in stack['Parameters']}
        proof={'beforeParameters':parameters,'beforeTemplate':before,'imageUri':image,'control':control,
            'changes':['ImageUri','PathGuard.FunctionCode'],'sourceSha256':build['sourceSha256']}
        (work/'runtime-review.json').write_bytes(encoded(proof))
        if parameters['ImageUri']==image and revised==edge:
            print('{"status":"runtime-already-current"}'); return
        response=cf.update_stack(StackName=args.stack,TemplateBody=json.dumps(old),
            Parameters=[{'ParameterKey':k,**({'ParameterValue':image} if k=='ImageUri' else {'UsePreviousValue':True})} for k in parameters],Capabilities=['CAPABILITY_IAM'])
        print(json.dumps({'status':'updating-runtime-and-bounded-public-paths','stackId':response['StackId']})); return
    if args.command=='install':
        review=json.loads((work/'live-review.json').read_text())
        if review['release']!=release or review['control']!=control or review['seconds']>90: raise ValueError('Runtime review changed or lacks headroom')
        if review['sources'].get('faaHistory',{}).get('status')!='ok' or not review['liveAirportProbabilities']: raise ValueError('FAA live feature validation incomplete')
        if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h for name,h in review['runtimeFiles'].items()): raise ValueError('Runtime code changed after review')
        from botocore.exceptions import ClientError
        for name,body in [('model.json',raw_model),('evaluation.json',raw_evaluation)]:
            key=f'active/operations/versions/{version}/{name}'
            try: s3.put_object(Bucket=out['Bucket'],Key=key,Body=body,ServerSideEncryption='AES256',ContentType='application/json',IfNoneMatch='*')
            except ClientError as error:
                if error.response['Error']['Code'] not in ('PreconditionFailed','412') or read(key)!=body: raise
        old_catalog=read('public/airports.json'); catalog=json.loads(old_catalog)
        (work/'catalog-before-install.json').write_bytes(old_catalog)
        catalog['operationsRelease']=release
        s3.put_object(Bucket=out['Bucket'],Key='public/airports.json',Body=encoded(catalog),ServerSideEncryption='AES256',
            ContentType='application/json',CacheControl='public,max-age=86400')
        (work/'install-receipt.json').write_bytes(encoded({'release':release,'control':control,'installedAt':datetime.now(timezone.utc).isoformat()}))
        print(json.dumps({'status':'operations-pair-installed','weatherDefaultPreserved':release['defaultModel']=='weather','version':version})); return
    manifest=json.loads(read('public/latest.json')); prefix='public/'+manifest['dataPrefix']+'/'
    snapshot=json.loads(read('state/latest.json')); risk=json.loads(read(prefix+'operations/risk.json'))
    if snapshot['generatedAt']!=manifest['generatedAt'] or risk['generatedAt']!=manifest['generatedAt'] or risk['version']!=version: raise ValueError('Operations publication is not current')
    if snapshot['sources'].get('faaHistory',{}).get('status')!='ok': raise ValueError('FAA history is unavailable')
    count=sum(any('probabilities' in v for d in a['directions'].values() for v in d.values()) for a in risk['airports'].values())
    if not count: raise ValueError('No operations probabilities in publication')
    proof={'status':'live-verified','generatedAt':manifest['generatedAt'],'liveAirportProbabilities':count,'sources':snapshot['sources'],
        'release':release,'control':control,'defaultModel':release['defaultModel']}
    review=json.loads((work/'runtime-review.json').read_text()); cf=session.client('cloudformation')
    stack=cf.describe_stacks(StackName=args.stack)['Stacks'][0]
    current=cf.get_template(StackName=args.stack,TemplateStage='Original')['TemplateBody']
    if isinstance(current,str): current=json.loads(current)
    expected=json.loads(json.dumps(review['beforeTemplate']))
    expected['Resources']['PathGuard']['Properties']['FunctionCode']=expected['Resources']['PathGuard']['Properties']['FunctionCode'].replace(r'evaluation\.json|stations',r'evaluation\.json|operations\/(?:risk|evaluation|release)\.json|stations')
    if current!=expected or control!=review['control']: raise ValueError('Unreviewed template or control change')
    params={p['ParameterKey']:p['ParameterValue'] for p in stack['Parameters']}
    if params!={**review['beforeParameters'],'ImageUri':review['imageUri']}: raise ValueError('Unreviewed stack parameter change')
    config=session.client('lambda').get_function_configuration(FunctionName=args.stack+'-collector')
    if config['MemorySize']!=1024 or config['Timeout']!=120: raise ValueError('Collector compute guard changed')
    proof['budgetComputeLeasePreserved']=True
    (work/'cloud-verification.json').write_bytes(encoded(proof))
    import airport_weather as weather
    weather.atomic_json(weather.STATE/'latest.json',snapshot); weather.publish(snapshot)
    print(json.dumps(proof))


if __name__=='__main__': main()
