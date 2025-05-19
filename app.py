#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.cdk_stack import CdkStack


app = cdk.App()
env = cdk.Environment(account="<YOUR_ACCOUNT_ID>", region="<YOUR_REGION>")
CdkStack(app, "CdkStack", env=env)

app.synth()