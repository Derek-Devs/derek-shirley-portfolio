"""One explicitly started, ten-minute image build. No schedules, webhooks, or paid-plan fallback."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from manage import ROOT, session_for, preflight, outputs
from template import policy, allow, role, ref, attr, sub

NAME = 'portfolio-airport-image-build'
PACKAGE = ROOT / '.airport-data/aws-package'


def prepare(reuse_repository=False):
    paths = [ROOT / 'infra/aws/Dockerfile', ROOT / 'infra/aws/Dockerfile.dockerignore',
             ROOT / 'infra/aws/limits.json', ROOT / 'research/requirements.txt']
    for pattern in ('tools/*.py', 'infra/aws/runtime/*.py', 'research/airport-protocol*.json'):
        paths.extend(sorted(ROOT.glob(pattern)))
    PACKAGE.mkdir(exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(PACKAGE / 'build-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            body = path.read_bytes(); name = path.relative_to(ROOT).as_posix()
            if len(body) > 2 * 1024 * 1024: raise ValueError('Unexpected build input size')
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, body)
            manifest[name] = hashlib.sha256(body).hexdigest()
    digest = hashlib.sha256((PACKAGE / 'build-source.zip').read_bytes()).hexdigest()
    result = {'sourceSha256': digest, 'sourceKey': f'source/{digest}.zip', 'files': manifest,
              'imageTag': 'reviewed-' + digest[:16], 'maximumBuildMinutes': 10, 'maximumBuilds': 1}
    (PACKAGE / 'build-inputs.json').write_text(json.dumps(result, indent=2) + '\n')
    (PACKAGE / 'build-cloudformation.json').write_text(json.dumps(build_template(reuse_repository), indent=2) + '\n')
    print(json.dumps(result))


def build_template(reuse_repository=False):
    r = {}
    r['Source'] = {'Type': 'AWS::S3::Bucket', 'Properties': {
        'PublicAccessBlockConfiguration': {k: True for k in ('BlockPublicAcls', 'BlockPublicPolicy', 'IgnorePublicAcls', 'RestrictPublicBuckets')},
        'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
        'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]},
        'LifecycleConfiguration': {'Rules': [{'Id': 'BuildSource', 'Status': 'Enabled', 'ExpirationInDays': 1}]}}}
    r['Image'] = {'Type': 'AWS::ECR::Repository', 'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain', 'Properties': {
        'RepositoryName': 'portfolio-airport-weather', 'ImageTagMutability': 'IMMUTABLE',
        'ImageScanningConfiguration': {'ScanOnPush': False}, 'EncryptionConfiguration': {'EncryptionType': 'AES256'},
        'RepositoryPolicyText': policy([{'Effect': 'Allow', 'Principal': {'Service': 'lambda.amazonaws.com'},
            'Action': ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
            'Condition': {'ArnLike': {'aws:SourceArn': sub('arn:aws:lambda:us-east-2:${AWS::AccountId}:function:portfolio-airport-weather-*')}}}])}}
    r['BuildLog'] = {'Type': 'AWS::Logs::LogGroup', 'Properties': {'LogGroupName': '/aws/codebuild/' + NAME, 'RetentionInDays': 7}}
    r['BuildRole'] = role('codebuild.amazonaws.com', [
        allow('s3:GetObject', sub('${Source.Arn}/source/*')),
        allow('ecr:GetAuthorizationToken', '*'),
        allow(['ecr:BatchCheckLayerAvailability', 'ecr:InitiateLayerUpload', 'ecr:UploadLayerPart',
               'ecr:CompleteLayerUpload', 'ecr:PutImage'], attr('Image', 'Arn')),
        allow(['logs:CreateLogStream', 'logs:PutLogEvents'], attr('BuildLog', 'Arn'))])
    smoke = ('import handler, learning, learning_v3, stop, airport_train_v2, airport_prepare_v2, airport_train_v3, airport_prepare_v3, airport_operations, airport_faa_history, airport_faa_collect, airport_operations_score; '
             'import numpy, pandas, scipy, sklearn, boto3; '
             'assert "GetAccountPlanState" in boto3.session.Session()._session.get_service_model("freetier").operation_names; '
             'assert handler.main({"untrusted":True},None)["status"]=="rejected-event"; print("Linux read-only import smoke passed")')
    spec = {'version': 0.2, 'phases': {
        'pre_build': {'commands': ['aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin "$REGISTRY"']},
        'build': {'commands': [
            'docker build --platform linux/amd64 -f infra/aws/Dockerfile -t "$IMAGE_URI" .',
            'docker run --rm --read-only --tmpfs /tmp:rw,size=256m -e JOB=collector --entrypoint python "$IMAGE_URI" -c ' + "'" + smoke + "'",
            'docker push "$IMAGE_URI"']}}}
    r['Build'] = {'Type': 'AWS::CodeBuild::Project', 'Properties': {
        'Name': NAME, 'ServiceRole': attr('BuildRole', 'Arn'), 'Artifacts': {'Type': 'NO_ARTIFACTS'},
        'Source': {'Type': 'S3', 'Location': sub('${Source}/unused.zip'), 'BuildSpec': json.dumps(spec)},
        'Environment': {'Type': 'LINUX_CONTAINER', 'ComputeType': 'BUILD_GENERAL1_SMALL',
            'Image': 'aws/codebuild/standard:7.0', 'PrivilegedMode': True, 'ImagePullCredentialsType': 'CODEBUILD'},
        'TimeoutInMinutes': 10, 'QueuedTimeoutInMinutes': 5, 'ConcurrentBuildLimit': 1,
        'LogsConfig': {'CloudWatchLogs': {'Status': 'ENABLED', 'GroupName': ref('BuildLog')}}}}
    result = {'AWSTemplateFormatVersion': '2010-09-09', 'Description': 'One-off bounded image build; delete after completion, retain immutable image.',
            'Resources': r, 'Outputs': {k: {'Value': v} for k, v in {
                'SourceBucket': ref('Source'), 'RepositoryUri': attr('Image', 'RepositoryUri'),
                'BuildProject': ref('Build'), 'BuildLog': ref('BuildLog')}.items()}}
    if reuse_repository:
        del r['Image']
        for statement in r['BuildRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']:
            if statement['Resource']==attr('Image','Arn'):
                statement['Resource']=sub('arn:aws:ecr:us-east-2:${AWS::AccountId}:repository/portfolio-airport-weather')
        result['Outputs']['RepositoryUri']['Value']=sub('${AWS::AccountId}.dkr.ecr.us-east-2.amazonaws.com/portfolio-airport-weather')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'bootstrap', 'start', 'status', 'cleanup'])
    p.add_argument('--profile'); p.add_argument('--account-id')
    p.add_argument('--reuse-repository',action='store_true')
    args = p.parse_args(); args.stack = NAME
    if args.command == 'prepare': return prepare(args.reuse_repository)
    session = session_for(args)
    cf = session.client('cloudformation'); cb = session.client('codebuild'); s3 = session.client('s3')
    if args.command == 'bootstrap':
        preflight(session, args)
        response = cf.create_stack(StackName=NAME, TemplateBody=json.dumps(build_template(args.reuse_repository)),
                                   Capabilities=['CAPABILITY_IAM'], OnFailure='ROLLBACK',
                                   Tags=[{'Key': 'Project', 'Value': 'airport-weather-temporary-build'}])
        print(json.dumps({'status': 'creating-build-resources', 'stackId': response['StackId']})); return
    if args.command == 'status':
        stack = cf.describe_stacks(StackName=NAME)['Stacks'][0]
        print(json.dumps({'stackStatus': stack['StackStatus']}))
        if stack['StackStatus'] != 'CREATE_COMPLETE': return
        history = cb.list_builds_for_project(projectName=NAME, sortOrder='DESCENDING')['ids']
        if not history: return
        build = cb.batch_get_builds(ids=[history[0]])['builds'][0]
        print(json.dumps({k: build.get(k) for k in ('id', 'buildStatus', 'currentPhase', 'phases', 'logs')}, default=str)); return
    out = outputs(session, NAME)
    inputs = json.loads((PACKAGE / 'build-inputs.json').read_text())
    if args.command == 'start':
        preflight(session, args)
        if cb.list_builds_for_project(projectName=NAME)['ids']:
            raise ValueError('This project has already run its one build; inspect it instead of retrying')
        body = (PACKAGE / 'build-source.zip').read_bytes()
        if hashlib.sha256(body).hexdigest() != inputs['sourceSha256']: raise ValueError('Build source hash changed')
        s3.put_object(Bucket=out['SourceBucket'], Key=inputs['sourceKey'], Body=body, ServerSideEncryption='AES256', IfNoneMatch='*')
        image_uri = out['RepositoryUri'] + ':' + inputs['imageTag']
        result = cb.start_build(projectName=NAME, sourceLocationOverride=out['SourceBucket'] + '/' + inputs['sourceKey'],
            idempotencyToken=inputs['sourceSha256'], environmentVariablesOverride=[
                {'name': 'IMAGE_URI', 'value': image_uri, 'type': 'PLAINTEXT'},
                {'name': 'REGISTRY', 'value': out['RepositoryUri'].split('/')[0], 'type': 'PLAINTEXT'}])
        receipt = {'buildId': result['build']['id'], 'imageTagUri': image_uri, **out, **inputs}
        (PACKAGE / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'buildId': receipt['buildId'], 'imageTagUri': image_uri})); return
    receipt = json.loads((PACKAGE / 'build-receipt.json').read_text())
    if receipt['BuildProject'] != NAME or receipt['SourceBucket'] != out['SourceBucket']: raise ValueError('Wrong build receipt')
    build = cb.batch_get_builds(ids=[receipt['buildId']])['builds'][0]
    if build['buildStatus'] == 'IN_PROGRESS': raise ValueError('Do not remove a running build')
    if build['buildStatus'] == 'SUCCEEDED':
        detail = session.client('ecr').describe_images(repositoryName='portfolio-airport-weather',
                  imageIds=[{'imageTag': receipt['imageTag']}])['imageDetails'][0]
        receipt['imageUri'] = out['RepositoryUri'] + '@' + detail['imageDigest']
        receipt['imageBytes'] = detail['imageSizeInBytes']
    receipt['buildStatus'] = build['buildStatus']
    receipt['phases'] = build.get('phases', [])
    log = session.client('logs').get_log_events(logGroupName=build['logs']['groupName'],
        logStreamName=build['logs']['streamName'], startFromHead=True, limit=1000)
    (PACKAGE / 'linux-build.log').write_text('\n'.join(e['message'] for e in log['events']), encoding='utf-8')
    (PACKAGE / 'build-receipt.json').write_text(json.dumps(receipt, indent=2, default=str) + '\n')
    keys = s3.list_objects_v2(Bucket=out['SourceBucket'])
    if keys.get('IsTruncated') or any(x['Key'] != receipt['sourceKey'] for x in keys.get('Contents', [])):
        raise ValueError('Unexpected source objects; refuse cleanup')
    s3.delete_object(Bucket=out['SourceBucket'], Key=receipt['sourceKey'])
    cf.delete_stack(StackName=NAME)
    print(json.dumps({'status': 'removing-temporary-build-resources', 'imageUri': receipt.get('imageUri')}))


if __name__ == '__main__': main()
