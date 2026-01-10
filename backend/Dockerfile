FROM public.ecr.aws/lambda/python:3.12

# uv
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /bin/uv
COPY pyproject.toml uv.lock ./

RUN uv pip install --system --no-cache -r pyproject.toml

# copy function code
COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]
