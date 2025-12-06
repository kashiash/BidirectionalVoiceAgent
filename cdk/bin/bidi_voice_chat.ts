#!/usr/bin/env node
import * as cdk from "aws-cdk-lib"
import { VoiceAgentBackendStack } from "../lib/backend"

const app = new cdk.App()
const _ = new VoiceAgentBackendStack(app, "VoiceAgentBackendStack", {})