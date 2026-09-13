# AWS operating plan and deployment runbook

## September 12 nationwide FAA model update

The optional operations model adds recent FAA advisory history to locally fitted
weather models at 97 supported major airports. Weather remains the default after
comparison with the actual incumbent. See [the national evaluation](airport-operations-us-v1.md).
Normal collection now makes four provider requests; previous-day finalization
and monthly runway refresh bring the maximum to six. No new scheduled job or
paid API was added. Operations weights stay fixed pending a future reviewed
evaluation; hourly updates refresh inputs, not fitted weights.

`infra/aws/deploy_faa_model.py` reviews and installs a versioned operations pair,
then updates only the immutable runtime image and the bounded public path
allowlist. It preserves the actual deployed template, all other parameters,
control state, lease, and the 3,008-MB learning worker. Use its `verify` command
for this release; the older context-only verifier predates operations files.
Receipts are in `.airport-data/operations-us-v1/`. The website itself remains
local. The following context-update section records the preceding release.

## September 12 operations-context update

The hourly collector now fetches the FAA's public airport-status XML alongside
the two weather feeds and refreshes OurAirports runway inventory once per
calendar month. It reuses the existing static station files and archived
snapshots. Data subscription fees remain $0. Normal collection makes three
provider requests; an inventory refresh makes at most four. Source-specific
byte/time limits and publication limits are documented in
`airport-operations-data.md` and enforced by the collector.

`deploy_operations.py` installs only a reviewed immutable image using the
existing CloudFormation template and all prior non-image parameters. It verifies
the active model/evaluation, Free plan, early-stop budget, and unexpired lease;
it cannot extend that lease or reset a collection slot. The deployed collector
remains 1,024 MB / 120 seconds and the learning worker remains 3,008 MB / 900
seconds. FAA/runway fields are observed context, not new production features.

The bounded image build passed its Linux import check and temporary build
resources were deleted. Receipts live under
`.airport-data/aws-package/operations-*.json`. For later verification, use:

```powershell
./.airport-data/aws-env/Scripts/python.exe infra/aws/deploy_operations.py verify --profile portfolio-airport --account-id 552969574724
```

The `collect` command uses the next available hourly slot and refuses an already
reserved hour. Manual invocation does not bypass the worker's persistent quota.
The website source remains local; these deployment commands update only its
shared AWS data collector.

Status: **AWS service live as of September 11, 2026** at `https://d3fuhsnkvtfott.cloudfront.net`. The dedicated GitHub-linked project is **Index Zero**, using `derek@derekdevs.com` in `us-east-2`. Browser and API verification confirmed an ACTIVE FREE account plan expiring March 11, 2027. The account initially had $100 in credits and received another $40 during setup. Temporary CLI access uses the `portfolio-airport` profile. The local configuration and `netlify.toml` now point to the live service; the public portfolio has not been republished. Its existing hosting stays in place.

The initial operating lease expires **October 12, 2026 at 23:34 UTC**. Collection and learning stop doing work after that time unless an operator reviews spend and quality and explicitly renews the lease. This is separate from the longer AWS Free account trial. It does not auto-renew.

## Scope

An hourly Lambda job collects the two free NOAA bulk feeds for the 933-airport U.S. and territories catalog (100 large, 833 medium). Missing reports remain missing. It assesses 100 major airports and scores supported horizons at 97 airports and publishes a complete generation of weather, risk, and evaluation files to private S3. CloudFront serves those static files. Airport selection and visitor traffic never invoke the worker or trigger a provider request. Self-hosted map geography and historical replay stay on the portfolio host.

A monthly Lambda job can ingest up to two missing BTS/IEM months, then train a challenger when two new outcome months are available. The expanded worker fits airport-local challengers across the reviewed 100-airport scope. Airports and horizons without sufficient evidence remain withheld. Private aviation remains weather context only.

The expanded job uses fixed airport-local regularized logistic challengers with 18 training months, six probability-calibration months, six interval-calibration months, and two later evaluation months. Monthly boundary exclusions and forecast availability lags remain. New outcome months are marked consumed before fitting, so a timeout cannot start repeated tuning of the same test. The expanded operational seed includes October–December 2025, closing the original gaps without using those months in the current v3 experiment. The next challenger still requires two genuinely new outcome months after June 2026.

The monthly role can write history and candidates but **cannot write the active model or public scores**. Candidate results report comparisons with the incumbent, airport regressions, calibration, uncertainty coverage, and sample support. Promotion requires reviewing the full artifact and synchronizing the portfolio methodology with the approved model. Neither weather changes nor an aggregate accuracy gain silently replaces production. No claim of fully automated continuous model improvement is made.

## Operating limits

The source of truth is `infra/aws/limits.json`; regenerate CloudFormation after edits.

| Control | Setting |
|---|---|
| Hourly worker | 1 GB RAM, 120 seconds, concurrency 1, at most 744 reservations/month |
| Monthly learner | 3,008 MB RAM, 900 seconds, concurrency 1, at most one reservation/month |
| Provider requests | Four per ordinary run, at most six with FAA day finalization and runway refresh; at most ten research requests per learning run |
| Failed jobs | No scheduler or Lambda function-error retries; persistent slot reservations reject duplicates |
| History download | Two source months/run; 96 MiB compressed BTS, 768 MiB expanded BTS, existing bounded TAF batches |
| Learning data | At most 72 indexed months, 1.6 million streamed windows, 100 audited airports; one airport is fitted at a time |
| Publication | At most 400 files and 16 MiB per generation; model weights stay private |
| Weather archive | At most 2 MiB compressed/hour, expires after 400 days |
| Public generations | Expire after seven days; manifest changes only after all files succeed |
| Logs / candidates | Seven-day logs; 90-day candidate retention |
| Initial activation | 31 days; no automatic renewal |
| Budget notifications | $2 and $4; automatic worker stop after reported spend exceeds $8 |
| Billing protection | AWS must report the exact account as **ACTIVE FREE**, with credits and a future expiry |
| Build | One manually started small CodeBuild worker; ten-minute build timeout; no recurring build |

Every job reserves quota in a DynamoDB transaction before data access. Disabled, expired, missing, corrupt, or unreachable control state prevents work. Reservations are not refunded after failure. Worker IAM permissions cannot reset the control switch or their counters. The two schedule targets are the only provisioned invocation permissions; there is no API Gateway, function URL, VM, NAT gateway, GPU, provisioned Lambda concurrency, model endpoint, or autoscaling service.

After reserving quota, each worker checks `freetier:GetAccountPlanState`. Paid, expired, missing, exhausted, or unverifiable plan state prevents weather downloads, model fitting, and publication. Deployment, seeding, and activation also check the live API. Activation cannot extend past an hour before the Free plan expires. The workers have no permission to upgrade the account plan.

The budget stop disables both schedules, sets worker concurrency to zero, and turns off the persistent control switch. An independent AWS Budgets IAM action denies the worker roles access to S3 and DynamoDB. The stop is sticky; month rollover does not renew the activation lease or enable the control switch. Stopped data becomes visibly stale, and the website withholds old probabilities after 90 minutes. S3 retention and the small fixed DynamoDB allocation can still incur charges while workers are paused.

## Cost estimate and the $20 limit

Estimate for this configuration, excluding existing website hosting and without assuming promotional credits:

| Item | Monthly allowance / estimate |
|---|---:|
| Hourly Lambda, even if all 744 runs hit 120 seconds | About $1.49 |
| One 3,008 MB / 900-second learning run | About $0.05 |
| S3 requests and bounded storage | Allow $1–$3 |
| DynamoDB 1 read / 1 write provisioned unit | About $0.58 before applicable free allowances |
| One small private ECR image, limited logs and notifications | Allow $0.50 |
| CloudFront requests and delivery | Variable metered usage; consumes Free-plan allowances/credits |
| Core processing/storage estimate | **Approximately $3–$6/month equivalent usage**, excluding delivery |
| Current user charges | **$0 while the AWS Free account plan remains active** |

The usage estimates are not a permanent all-in bill ceiling. The current protection is the AWS **Free account plan**: AWS states that it incurs no charges and closes the account when credits are exhausted or six months elapse, whichever comes first. This is a protected trial, not a perpetual free service. Unusual public traffic can consume credits and shorten availability. No paid upgrade is authorized or performed. [AWS account plans](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html).

[Lambda pricing](https://aws.amazon.com/lambda/pricing/), [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/), [S3 pricing](https://aws.amazon.com/s3/pricing/), and [ECR pricing](https://aws.amazon.com/ecr/pricing/) support the core estimate. CloudFront uses standard metering under the account's no-charge Free plan. The separate CloudFront flat-rate Free subscription is not used; it is unavailable to Free-plan accounts.

**The user's ongoing limit remains $20 maximum.** `manage.py` now verifies the live Free account plan rather than accepting a manual claim of billing protection. AWS Budgets reports can lag usage, so the $8 action remains an early stop, not a contractual $20 cap. [AWS Budgets timing](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html).

Continuing beyond the trial requires a separate billing review and user decision. AWS's paid-project spend limit has a minimum of $20 and applies before tax, so it does not automatically satisfy a $20 all-in limit. The current scripts reject paid plans even if credits remain. Do not upgrade the project merely to keep the service running. [AWS project spend limits](https://docs.aws.amazon.com/accounts/latest/reference/create-spend-limit.html).

The local Docker engine cannot start because WSL reports `HCS_E_HYPERV_NOT_INSTALLED`. No Windows features, BIOS settings, or restart were changed. `build_image.py` prepares an explicit source allowlist (Python tools, runtime, protocols, requirements, Dockerfile), excluding credentials, Git data, private archives, and the rest of the portfolio. Its temporary CodeBuild project permits one manually started small build, ten minutes maximum, with no webhook, schedule, fleet, or image server. A ten-minute general1.small build is at most $0.05 in base compute before allowances; the verified Free account plan covers charges. [CodeBuild pricing](https://aws.amazon.com/codebuild/pricing/).

The first disabled-stack attempt was rolled back after Lambda rejected the 4 GB learner allocation. This project currently permits at most 3,008 MB. CloudFormation now applies the lower of the reviewed memory ceiling and 3,008 MB. The immutable runtime image's 4 GB ceiling is not an allocation request; actual allocation is controlled by the template. Full monthly training memory still needs measurement, and a failed training attempt cannot promote a model or reset its monthly reservation.

## Deployment sequence

### New GitHub / Builder ID account compatibility

The [new AWS sign-up experience](https://docs.aws.amazon.com/accounts/latest/reference/sign-in-new.html) uses the existing GitHub-linked Builder ID. First-project setup and temporary CLI authentication are complete.

The new experience [assigns a single region](https://docs.aws.amazon.com/accounts/latest/reference/project-regions.html) and does not support WAF with CloudFront. The template now targets the verified `us-east-2` project region and uses private S3, CloudFront origin access control, caching, and a function that limits public paths to the catalog and recent snapshots. WAF and the separate CloudFront flat-rate plan are not provisioned. The verified no-charge account plan supplies the billing protection; the path guard does not guarantee a traffic ceiling.

**Do not activate advanced AWS features to work around those restrictions.** [Activation is irreversible and removes project spend limits](https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.html). That would undermine the budget protection being evaluated. A paid-plan upgrade and advanced-feature activation are separate changes; neither has been performed.

Access uses the official signed AWS CLI and `aws login --region us-east-2 --profile portfolio-airport`, then verifies the exact account with STS. Credentials remain in AWS's user-profile cache, outside the repository and OneDrive. The isolated local SDK uses `boto3[crt]` for this login provider. No agent toolkit, GitHub workflow, or persistent access key is installed. [Temporary AWS CLI access](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html).

### Account and resource setup

1. Sign in with the named temporary profile. The scripts reject root credentials and require the exact new account ID. Never send passwords, access keys, payment details, or MFA codes in chat.
2. Run `manage.py preflight --profile PROFILE --account-id ACCOUNT`. It checks the live Free account plan, credits, expiry, and Lambda concurrency quota before cloud creation.
3. Run `python infra/aws/manage.py prepare` to validate hashes and produce `.airport-data/aws-package/seed.zip` and its file manifest. The expanded seed contains portable active artifacts and 42 derived history months (39 research months plus three operational gap months), not credentials or raw passenger data.
4. Install development tooling in an isolated venv using `infra/aws/requirements-dev.txt`. With a running Linux Docker engine, build from the repository root:

   ```powershell
   docker build --platform linux/amd64 -f infra/aws/Dockerfile -t portfolio-airport-weather:reviewed .
   ```

   For the current machine, use `build_image.py prepare`, `bootstrap`, `status`, and `start` with the named profile/account. Wait for stack completion before `start`. The script refuses a second build in the same project. The Linux build verifies scientific imports and runtime imports with a read-only filesystem before pushing. `cleanup` records the immutable image digest and removes the temporary project, source bucket, build role, and logs; the ECR image is retained for Lambda. Inspect failures before considering another build. Never use `latest` as the deployment reference.
5. `manage.py bootstrap --profile PROFILE --account-id ACCOUNT --image-uri IMMUTABLE_ECR_URI` creates the stack with jobs, concurrency, and delivery **disabled**. Check CloudFormation completion and failures; do not remove caps to work around errors.
6. `manage.py seed` with the same account/profile uploads only to an empty new bucket and creates a disabled control record. Interrupted bootstrap requires inspection; seed deliberately refuses to overwrite an existing bucket, history frontier, or active model.
7. Confirm the budget email subscription. Inspect the private bucket, origin-access policy, schedules, roles, and limits.
8. Run `manage.py inspect --profile PROFILE --account-id ACCOUNT`. It checks the live Free account plan and $8 budget. `manage.py activate` requests the enabled stack state and a lease of at most 31 days. Wait for successful stack update, then verify the first complete weather generation and both job configurations.
9. Set `PUBLIC_AIRPORT_DATA_URL` on the existing portfolio host to the stack's `https://…cloudfront.net` output. Build and publish the portfolio once through its existing deployment workflow. No hourly site rebuild is needed. The endpoint is public configuration, never a secret. With the variable absent, the current local snapshot behavior is unchanged.
10. Verify CORS, global weather coverage, model/evaluation hashes, fresh/stale behavior, and a simulated budget stop before considering the service live. Confirm actual first-day costs. Renew the initial lease only after reviewing spend and quality. `manage.py pause --profile PROFILE --account-id ACCOUNT` stops workers without requiring a billing review.

Candidate promotion is intentionally not an automated command. Review candidate files, per-airport regressions, source history, the unchanged serving thresholds, and a fresh shadow period before changing `active/` artifacts. Update the portfolio's scientific description in the same reviewed release. Preserve the previous active pair for rollback. Do not reinitialize the history frontier to reuse an inspected holdout.

For teardown, pause workers first, disable delivery, then inspect and delete the project's stack and retained repository. The bucket uses `Retain`; archive/export anything needed before explicitly deleting that bucket. Retained objects and images are not removed by worker shutdown. There is no separate CloudFront subscription to cancel.

## Verification completed

CloudFormation schema validation passes for `us-east-2`. Sixteen AWS tests cover persistent quota reservations, month rollover, fail-closed handling, rejected payloads, Free account plan validation, stopping before downloads/training when plan verification fails, SDK schemas, atomic publication, model hashes, bounded paths/bytes, disjoint learning periods, IAM publishing restrictions, CORS header overrides for the shared cache, and an offline collection across the 933 U.S. and territory airports. The live preflight successfully checked the actual Free plan and Lambda quota.

The immutable Linux image passed scientific-library and runtime imports with a read-only filesystem. Its temporary CodeBuild project, source bucket, build role, and logs were removed after the successful build; the ECR image remains for Lambda.

The live shutdown drill disabled both schedules, set both worker concurrency limits to zero, and disabled the control record. The replacement budget-alert email subscription was verified confirmed before activation. After reactivation, both schedules and their concurrency limits were verified enabled, and CloudFront reported Deployed.

The hourly schedule published its first generation at **23:35:08 UTC on September 11**: 5,077 catalog airports, 2,838 available observations, 2,652 available forecasts, and 311 public files. The collector took **14.779 seconds** (15.175 billed seconds including startup), with **210 MB maximum memory** out of 1,024 MB. Both NOAA downloads succeeded. A later manual invocation in the same hour correctly returned paused: the durable slot reservation rejected duplicate work. Its verification command returned an error because it expected a new publication; this was not a collection failure. No quota was reset and no extra provider requests were made.

Public endpoint checks confirmed HTTP 200 and local-preview CORS for the manifest, catalog, risk, evaluation, and DFW station partition. The generation timestamps agree; the cloud evaluation equals the reviewed local evaluation. The private model URL returns 404. Evidence is saved under `.airport-data/aws-package/` in `public-snapshot-verification.json`, `stop-drill-verification.json`, `collect-verification.json`, and the build receipt. The production portfolio build passes with the saved AWS endpoint.

Browser verification on the local page confirmed the 23:35 UTC cloud snapshot, automatic DFW/ORD selection, departure and arrival outcomes, airport-specific backtest metrics, and the world map. Heathrow displays its available weather with no untested airline probabilities. Sparse DFW overnight windows correctly withhold estimates, while a supported T−12 window displays them. No browser errors or warnings were recorded. The final live configuration is saved in `audit-verification.json`; the successful scheduled collection and rejected duplicate are preserved in `first-collector.log`.

A production-domain check caught S3's local-preview CORS header being reused from CloudFront's shared cache. The deployed custom response-header policy now overrides origin headers for each allowed viewer origin. All 15 checks across five public file types and the three allowed origins pass, including cache hits, in `cors-verification.json`. The CloudFormation update completed successfully and changed only the response policy and its distribution association; it did not renew the operating lease or alter workers, budgets, quotas, or the immutable image. [AWS response-header override behavior](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-response-headers-policies.html).

The monthly schedule is enabled for 10:00 UTC on the 15th. Full training on the actual 3,008 MB Lambda allocation has **not** been measured, and no new challenger has been trained in AWS yet. Monthly full training on two new future outcome months cannot be claimed before those labels arrive. No model has been automatically promoted. First-day billing is subject to AWS reporting delay; account-plan protection is verified, not inferred from a same-day zero usage report.

## U.S. scope revision — September 11, 2026

The local and cloud catalogs now contain 933 U.S. and territory airports, including 100 large airports. These catalog classifications are a planning envelope; BTS reporting coverage and forecast availability determine which airport/horizon models can be supported. Medium airports remain available for private-aviation weather. The current published model and its 25-airport evaluation have not changed.

The existing cloud collector reads the narrowed catalog on each hourly run, so subsequent weather state and archives are restricted to these airports. NOAA's two public bulk downloads still contain international source records; international airport weather is not selected for the new snapshots. Existing archived generations retain their original timestamps and expire under their existing retention rules. The browser also filters old cached catalogs, and the CloudFront station-prefix allowlist has been narrowed. Neighboring countries may appear as geographic context on the map.

`infra/aws/scope_us.py` previews this migration; `--apply` updates only the catalog, existing snapshot coverage counts, and the CloudFront path allowlist. It verifies the Free account and budget, uses conditional S3 writes, and preserves model artifacts, snapshot timestamps, resource configuration and spending controls. It does not retrain or activate anything. The Lambda image was not rebuilt: the deployed collector already selects stations from the catalog. The extra source-code country check will also apply to future image builds.

For roughly 100 supported airport models, the separate sizing allowance of 30–300 seconds per airport at 3,008 MB implies about $0.15–$1.47 per monthly fitting/evaluation cycle, excluding preparation. A $5–$15/month core operating target is plausible with bounded processing and modest traffic; it is not a guaranteed bill. Initial preparation and expanded validation should run locally before reviewing any changes to the current 25-airport/cloud learning limits. Data subscriptions remain $0. All new airport probabilities require their own time-based tests and calibration; a scope change alone does not supply those results.
