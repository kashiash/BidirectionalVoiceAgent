# CDK Stack

CDK Stack for deploying AgentCore Runtime Endpoint

## Commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template
* `npx cdk destroy`   Destroy CloudFormation template


## Additional Configurations

Following environment variables can be set on the endpoint, within the [stack](./lib/backend.ts)

```ts
MODEL_ID = "amazon.nova-2-sonic-v1:0"
INPUT_SAMPLE_RATE = "16000"
OUTPUT_SAMPLE_RATE = "16000"
CHANNELS = "1"
```

Make sure that the ones set on the endpoint matches that on the [CLI app](../cli/app/main.py).