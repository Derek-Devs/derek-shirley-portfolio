FROM public.ecr.aws/lambda/python:3.12
COPY research/requirements.txt /tmp/research-requirements.txt
RUN pip install --no-cache-dir -r /tmp/research-requirements.txt
RUN pip install --no-cache-dir boto3==1.43.93
COPY tools/ ${LAMBDA_TASK_ROOT}/tools/
COPY research/airport-protocol*.json ${LAMBDA_TASK_ROOT}/research/
COPY infra/aws/runtime/ ${LAMBDA_TASK_ROOT}/
COPY infra/aws/limits.json ${LAMBDA_TASK_ROOT}/limits.json
RUN mkdir -p ${LAMBDA_TASK_ROOT}/.airport-data/model-v2/candidate ${LAMBDA_TASK_ROOT}/.airport-data/model
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
CMD ["handler.main"]
