# Full Featured CLI Client Voice Chat App

## Set up

```bash
uv venv
source .venv/bin/activate
uv sync
```

## Run the app
```bash
# connecting to ws://localhost:8080/ws
.venv/bin/python app/main.py
# connecting to agent core runtime.
# Make sure to have AWS Credential set in the environment through AWS CLI
.venv/bin/python app/main.py --agent_arn 'arn:aws:bedrock-agentcore:ap-northeast-1:...:runtime/...'
```

### Arguments
1. `debug`: setting this to True will print out all the event types received.
2. `endpoint`: If you have a specific ws endpoint to connect to without the needs of any credentials. Default to `ws://localhost:8080/ws` for easy local debugging.
3. `agent_arn`: the AgentCore Runtime ARN we got above. If this is not specified, will use `endpoint` instead.


## NOTE
When connecting to AgentCore runtime, this app assumes that the inbound authorization is set to IAM, ie: using AWS credentails. If it is set to OAuth2 instead, please make modification on websocket.connect accordingly as described in [invoke-deployed-websocket](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html#step-4-invoke-deployed-websocket).