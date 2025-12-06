#  Backend Voice Agent Endpoint

## Set up

```bash
uv venv
source .venv/bin/activate
uv sync
```

## Start local server

```bash
# Make sure to have AWS Credential set in the environment through AWS CLI
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080
```

You can then use the [CLI](../cli/) app to connect to it and test it out.


## Test With Docker

### Build the image
```bash
docker buildx create --use
docker buildx build --platform linux/arm64 -t backend-agent:arm64 --load .
```

### run docker
```bash
docker run --platform linux/arm64 -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -e AWS_REGION="$AWS_REGION" \
  backend-agent:arm64
```