"""Generate reviewable CloudFormation JSON. Does not contact AWS or deploy anything."""
import json
from pathlib import Path

HERE = Path(__file__).parent
LIMITS = json.loads((HERE / 'limits.json').read_text())
PUBLIC_ORIGINS = ['https://www.derekdevs.com', 'https://derekdevs.com', 'http://127.0.0.1:4321']
ref = lambda name: {'Ref': name}
attr = lambda name, key: {'Fn::GetAtt': [name, key]}
sub = lambda value: {'Fn::Sub': value}


def policy(statements):
    return {'Version': '2012-10-17', 'Statement': statements}


def allow(actions, resources):
    return {'Effect': 'Allow', 'Action': actions, 'Resource': resources}


def role(service, statements):
    return {'Type': 'AWS::IAM::Role', 'Properties': {
        'AssumeRolePolicyDocument': policy([{'Effect': 'Allow', 'Principal': {'Service': service}, 'Action': 'sts:AssumeRole'}]),
        'Policies': [{'PolicyName': 'BoundedProjectAccess', 'PolicyDocument': policy(statements)}]}}


def build():
    t = {'AWSTemplateFormatVersion': '2010-09-09',
         'Description': 'Airport weather: private hourly collection and review-only monthly learning. Disabled until billing preflight.',
         'Parameters': {
             'ImageUri': {'Type': 'String', 'AllowedPattern': '[0-9]{12}\\.dkr\\.ecr\\.us-east-2\\.amazonaws\\.com/[a-z0-9/_-]+@sha256:[a-f0-9]{64}'},
             'ContactEmail': {'Type': 'String', 'Default': 'derek@derekdevs.com'},
             'EnableJobs': {'Type': 'String', 'Default': 'false', 'AllowedValues': ['false', 'true']},
             'EnableDelivery': {'Type': 'String', 'Default': 'false', 'AllowedValues': ['false', 'true']}},
         'Rules': {'ReviewedRegion': {'Assertions': [{'Assert': {'Fn::Equals': [ref('AWS::Region'), LIMITS['region']]}, 'AssertDescription': 'Deploy only in the reviewed project region.'}]}},
         'Conditions': {'JobsEnabled': {'Fn::Equals': [ref('EnableJobs'), 'true']}, 'DeliveryEnabled': {'Fn::Equals': [ref('EnableDelivery'), 'true']}},
         'Resources': {}, 'Outputs': {}}
    r = t['Resources']
    r['Data'] = {'Type': 'AWS::S3::Bucket', 'DeletionPolicy': 'Retain', 'UpdateReplacePolicy': 'Retain', 'Properties': {
        'PublicAccessBlockConfiguration': {k: True for k in ('BlockPublicAcls', 'BlockPublicPolicy', 'IgnorePublicAcls', 'RestrictPublicBuckets')},
        'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
        'BucketEncryption': {'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]},
        'CorsConfiguration': {'CorsRules': [{'AllowedOrigins': PUBLIC_ORIGINS, 'AllowedMethods': ['GET', 'HEAD'], 'AllowedHeaders': ['*'], 'MaxAge': 3600}]},
        'LifecycleConfiguration': {'Rules': [
            {'Id': 'Snapshots', 'Status': 'Enabled', 'Prefix': 'public/snapshots/', 'ExpirationInDays': LIMITS['snapshotRetentionDays']},
            {'Id': 'ForecastEvidence', 'Status': 'Enabled', 'Prefix': 'archive/', 'ExpirationInDays': LIMITS['forecastArchiveRetentionDays']},
            {'Id': 'Challengers', 'Status': 'Enabled', 'Prefix': 'candidates/', 'ExpirationInDays': LIMITS['candidateRetentionDays']},
            {'Id': 'IncompleteUploads', 'Status': 'Enabled', 'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1}}]}}}
    r['Control'] = {'Type': 'AWS::DynamoDB::Table', 'Properties': {'BillingMode': 'PROVISIONED',
        'ProvisionedThroughput': {'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1},
        'AttributeDefinitions': [{'AttributeName': 'id', 'AttributeType': 'S'}], 'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'TimeToLiveSpecification': {'AttributeName': 'expiresAt', 'Enabled': True}}}
    for logical, job, schedule in [('Collector', 'collector', 'rate(1 hour)'), ('Learning', 'learning', 'cron(0 10 15 * ? *)')]:
        r[logical + 'Log'] = {'Type': 'AWS::Logs::LogGroup', 'Properties': {'LogGroupName': sub('/aws/lambda/${AWS::StackName}-' + job), 'RetentionInDays': LIMITS['logRetentionDays']}}
        read_keys = ['active/*', 'public/airports.json', 'state/latest.json'] if job == 'collector' else ['active/*', 'history/*']
        write_keys = ['public/snapshots/*', 'public/latest.json', 'archive/*', 'state/latest.json'] if job == 'collector' else ['history/*', 'candidates/*']
        r[logical + 'Role'] = role('lambda.amazonaws.com', [
            allow('freetier:GetAccountPlanState', '*'),
            allow(['s3:GetObject'], [sub('${Data.Arn}/' + key) for key in read_keys]),
            allow(['s3:PutObject'], [sub('${Data.Arn}/' + key) for key in write_keys]),
            {**allow('dynamodb:ConditionCheckItem', attr('Control', 'Arn')),
             'Condition': {'ForAllValues:StringEquals': {'dynamodb:LeadingKeys': ['control']}}},
            {**allow('dynamodb:PutItem', attr('Control', 'Arn')),
             'Condition': {'ForAllValues:StringLike': {'dynamodb:LeadingKeys': [f'slot/{job}/*']}}},
            {**allow('dynamodb:UpdateItem', attr('Control', 'Arn')),
             'Condition': {'ForAllValues:StringLike': {'dynamodb:LeadingKeys': [f'quota/{job}/*']}}},
            allow(['logs:CreateLogStream', 'logs:PutLogEvents'], attr(logical + 'Log', 'Arn'))])
        r[logical] = {'Type': 'AWS::Lambda::Function', 'DependsOn': logical + 'Log', 'Properties': {
            'FunctionName': sub('${AWS::StackName}-' + job), 'Role': attr(logical + 'Role', 'Arn'),
            'PackageType': 'Image', 'Code': {'ImageUri': ref('ImageUri')}, 'Architectures': ['x86_64'],
            # The new project rejects allocations above 3008 MB. Stay below the reviewed ceiling.
            'Timeout': LIMITS[job]['timeoutSeconds'], 'MemorySize': min(LIMITS[job]['memoryMb'], 3008),
            'EphemeralStorage': {'Size': 1024 if job == 'learning' else 512},
            'ReservedConcurrentExecutions': {'Fn::If': ['JobsEnabled', 1, 0]},
            'Environment': {'Variables': {'DATA_BUCKET': ref('Data'), 'CONTROL_TABLE': ref('Control'), 'JOB': job, 'ACCOUNT_ID': ref('AWS::AccountId')}}}}
        r[logical + 'Retry'] = {'Type': 'AWS::Lambda::EventInvokeConfig', 'Properties': {'FunctionName': ref(logical), 'Qualifier': '$LATEST', 'MaximumRetryAttempts': 0, 'MaximumEventAgeInSeconds': 60}}
        r[logical + 'Schedule'] = {'Type': 'AWS::Events::Rule', 'Properties': {'ScheduleExpression': schedule,
            'State': {'Fn::If': ['JobsEnabled', 'ENABLED', 'DISABLED']},
            'Targets': [{'Id': job, 'Arn': attr(logical, 'Arn'), 'Input': json.dumps({'job': job}),
                         'RetryPolicy': {'MaximumRetryAttempts': 0, 'MaximumEventAgeInSeconds': 60}}]}}
        r[logical + 'Permission'] = {'Type': 'AWS::Lambda::Permission', 'Properties': {'Action': 'lambda:InvokeFunction',
            'FunctionName': ref(logical), 'Principal': 'events.amazonaws.com', 'SourceArn': attr(logical + 'Schedule', 'Arn'), 'SourceAccount': ref('AWS::AccountId')}}
    r['BudgetTopic'] = {'Type': 'AWS::SNS::Topic', 'Properties': {'Subscription': [{'Protocol': 'email', 'Endpoint': ref('ContactEmail')}]}}
    r['BudgetTopicPolicy'] = {'Type': 'AWS::SNS::TopicPolicy', 'Properties': {'Topics': [ref('BudgetTopic')], 'PolicyDocument': policy([
        {'Effect': 'Allow', 'Principal': {'Service': 'budgets.amazonaws.com'}, 'Action': 'sns:Publish', 'Resource': ref('BudgetTopic'),
         'Condition': {'StringEquals': {'aws:SourceAccount': ref('AWS::AccountId')}, 'ArnLike': {'aws:SourceArn': sub('arn:aws:budgets::${AWS::AccountId}:*')}}}])}}
    r['StopLog'] = {'Type': 'AWS::Logs::LogGroup', 'Properties': {'LogGroupName': sub('/aws/lambda/${AWS::StackName}-stop'), 'RetentionInDays': 7}}
    r['StopRole'] = role('lambda.amazonaws.com', [allow('dynamodb:UpdateItem', attr('Control', 'Arn')),
        allow('lambda:PutFunctionConcurrency', [attr('Collector', 'Arn'), attr('Learning', 'Arn')]),
        allow('events:DisableRule', [attr('CollectorSchedule', 'Arn'), attr('LearningSchedule', 'Arn')]),
        allow(['logs:CreateLogStream', 'logs:PutLogEvents'], attr('StopLog', 'Arn'))])
    r['Stop'] = {'Type': 'AWS::Lambda::Function', 'DependsOn': 'StopLog', 'Properties': {
        'FunctionName': sub('${AWS::StackName}-stop'), 'Role': attr('StopRole', 'Arn'), 'PackageType': 'Image', 'Code': {'ImageUri': ref('ImageUri')},
        'ImageConfig': {'Command': ['stop.main']}, 'Timeout': 30, 'MemorySize': 128, 'ReservedConcurrentExecutions': 1,
        'Environment': {'Variables': {'CONTROL_TABLE': ref('Control'), 'BUDGET_TOPIC': ref('BudgetTopic'),
            'WORKER_FUNCTIONS': {'Fn::Join': ['', ['["', ref('Collector'), '","', ref('Learning'), '"]']]},
            'WORKER_RULES': {'Fn::Join': ['', ['["', ref('CollectorSchedule'), '","', ref('LearningSchedule'), '"]']]}}}}}
    r['StopSubscription'] = {'Type': 'AWS::SNS::Subscription', 'Properties': {'Protocol': 'lambda', 'TopicArn': ref('BudgetTopic'), 'Endpoint': attr('Stop', 'Arn')}}
    r['StopPermission'] = {'Type': 'AWS::Lambda::Permission', 'Properties': {'Action': 'lambda:InvokeFunction', 'FunctionName': ref('Stop'), 'Principal': 'sns.amazonaws.com', 'SourceArn': ref('BudgetTopic'), 'SourceAccount': ref('AWS::AccountId')}}
    r['Budget'] = {'Type': 'AWS::Budgets::Budget', 'DependsOn': 'BudgetTopicPolicy', 'Properties': {
        'Budget': {'BudgetName': sub('${AWS::StackName}-early-stop'), 'BudgetType': 'COST', 'TimeUnit': 'MONTHLY',
                   'BudgetLimit': {'Amount': LIMITS['earlyStopUsd'], 'Unit': 'USD'},
                   'CostTypes': {'IncludeCredit': False, 'IncludeRefund': False, 'IncludeTax': True}},
        'NotificationsWithSubscribers': [{'Notification': {'NotificationType': 'ACTUAL', 'ComparisonOperator': 'GREATER_THAN', 'ThresholdType': 'ABSOLUTE_VALUE', 'Threshold': amount},
            'Subscribers': [{'SubscriptionType': 'EMAIL', 'Address': ref('ContactEmail')}] + ([{'SubscriptionType': 'SNS', 'Address': ref('BudgetTopic')}] if amount == 8 else [])} for amount in (2, 4, 8)]}}
    r['RuntimeDeny'] = {'Type': 'AWS::IAM::ManagedPolicy', 'Properties': {'PolicyDocument': policy([{'Effect': 'Deny', 'Action': ['s3:*', 'dynamodb:*'], 'Resource': '*'}])}}
    r['BudgetActionRole'] = role('budgets.amazonaws.com', [allow(['iam:AttachRolePolicy', 'iam:DetachRolePolicy', 'iam:ListAttachedRolePolicies'], [attr('CollectorRole', 'Arn'), attr('LearningRole', 'Arn')])])
    r['BudgetAction'] = {'Type': 'AWS::Budgets::BudgetsAction', 'Properties': {'BudgetName': ref('Budget'), 'ActionType': 'APPLY_IAM_POLICY',
        'ActionThreshold': {'Type': 'ABSOLUTE_VALUE', 'Value': 8}, 'ApprovalModel': 'AUTOMATIC', 'NotificationType': 'ACTUAL',
        'ExecutionRoleArn': attr('BudgetActionRole', 'Arn'), 'Definition': {'IamActionDefinition': {'PolicyArn': ref('RuntimeDeny'), 'Roles': [ref('CollectorRole'), ref('LearningRole')]}},
        'Subscribers': [{'Type': 'EMAIL', 'Address': ref('ContactEmail')}]}}
    r['OriginAccess'] = {'Type': 'AWS::CloudFront::OriginAccessControl', 'Properties': {'OriginAccessControlConfig': {'Name': sub('${AWS::StackName}-private-data'), 'OriginAccessControlOriginType': 's3', 'SigningBehavior': 'always', 'SigningProtocol': 'sigv4'}}}
    # Limit even plausible cache-miss paths to actual catalog buckets and seven days of hourly keys.
    airports = json.loads((HERE.parents[1] / 'public/data/airport-weather/airports.json').read_text(encoding='utf-8'))['airports']
    prefixes = sorted({a['icao'][:2] for a in airports})
    edge = """function handler(event) {
      var r=event.request, reject={statusCode:404,statusDescription:'Not Found'};
      if (/^\\/(latest|airports)\\.json$/.test(r.uri)) return r;
      var m=r.uri.match(/^\\/snapshots\\/(\\d{4})(\\d{2})(\\d{2})T(\\d{2})0000Z\\/(risk\\.json|evaluation\\.json|operations\\/(?:risk|evaluation|release)\\.json|stations\\/([A-Z0-9]{2})\\.json)$/);
      if (!m) return reject;
      var iso=m[1]+'-'+m[2]+'-'+m[3]+'T'+m[4]+':00:00Z', at=Date.parse(iso), now=Date.now();
      if (!isFinite(at) || new Date(at).toISOString().slice(0,19)!==iso.slice(0,19) || at>now+3600000 || at<now-7*86400000) return reject;
      var prefixes=PREFIXES;
      if (m[6] && prefixes.indexOf(m[6])<0) return reject;
      return r;
    }""".replace('PREFIXES', json.dumps(prefixes, separators=(',', ':')))
    r['PathGuard'] = {'Type': 'AWS::CloudFront::Function', 'Properties': {'Name': sub('${AWS::StackName}-public-paths'), 'AutoPublish': True,
        'FunctionConfig': {'Comment': 'Only bounded public data paths', 'Runtime': 'cloudfront-js-2.0'},
        'FunctionCode': edge}}
    # Override cached S3 CORS headers for each viewer's Origin. The shared cache omits Origin.
    r['PublicResponseHeaders'] = {'Type': 'AWS::CloudFront::ResponseHeadersPolicy', 'Properties': {
        'ResponseHeadersPolicyConfig': {'Name': sub('${AWS::StackName}-public-cors'),
            'Comment': 'Apply the allowed viewer origin even when S3 headers came from a different cached request',
            'CorsConfig': {'AccessControlAllowCredentials': False, 'AccessControlAllowHeaders': {'Items': ['*']},
                'AccessControlAllowMethods': {'Items': ['GET', 'HEAD']},
                'AccessControlAllowOrigins': {'Items': PUBLIC_ORIGINS}, 'OriginOverride': True},
            'SecurityHeadersConfig': {'ContentTypeOptions': {'Override': True}}}}}
    r['Distribution'] = {'Type': 'AWS::CloudFront::Distribution', 'Properties': {'DistributionConfig': {
        'Enabled': {'Fn::If': ['DeliveryEnabled', True, False]}, 'Comment': 'Requires ACTIVE FREE AWS account plan; no paid-plan upgrade',
        'Origins': [{'Id': 'data', 'DomainName': attr('Data', 'RegionalDomainName'), 'OriginPath': '/public', 'OriginAccessControlId': attr('OriginAccess', 'Id'), 'S3OriginConfig': {'OriginAccessIdentity': ''}}],
        'DefaultCacheBehavior': {'TargetOriginId': 'data', 'ViewerProtocolPolicy': 'redirect-to-https', 'AllowedMethods': ['GET', 'HEAD'], 'CachedMethods': ['GET', 'HEAD'], 'Compress': True,
            'CachePolicyId': '658327ea-f89d-4fab-a63d-7e88639e58f6', 'ResponseHeadersPolicyId': ref('PublicResponseHeaders'),
            'FunctionAssociations': [{'EventType': 'viewer-request', 'FunctionARN': attr('PathGuard', 'FunctionARN')}]},
        'ViewerCertificate': {'CloudFrontDefaultCertificate': True}, 'HttpVersion': 'http2', 'IPV6Enabled': True}}}
    r['BucketPolicy'] = {'Type': 'AWS::S3::BucketPolicy', 'Properties': {'Bucket': ref('Data'), 'PolicyDocument': policy([
        {'Effect': 'Allow', 'Principal': {'Service': 'cloudfront.amazonaws.com'}, 'Action': 's3:GetObject', 'Resource': sub('${Data.Arn}/public/*'),
         'Condition': {'StringEquals': {'AWS:SourceArn': sub('arn:aws:cloudfront::${AWS::AccountId}:distribution/${Distribution}')}}},
        {'Effect': 'Deny', 'Principal': '*', 'Action': 's3:*', 'Resource': [attr('Data', 'Arn'), sub('${Data.Arn}/*')], 'Condition': {'Bool': {'aws:SecureTransport': 'false'}}}])}}
    for name, value in {'Bucket': ref('Data'), 'ControlTable': ref('Control'), 'DistributionId': ref('Distribution'),
                        'DistributionArn': sub('arn:aws:cloudfront::${AWS::AccountId}:distribution/${Distribution}'),
                        'DataUrl': sub('https://${Distribution.DomainName}'), 'BudgetName': ref('Budget'), 'BudgetTopic': ref('BudgetTopic')}.items():
        t['Outputs'][name] = {'Value': value}
    return t


if __name__ == '__main__':
    path = HERE / 'cloudformation.json'
    path.write_text(json.dumps(build(), indent=2) + '\n', encoding='utf-8')
    print(path)
