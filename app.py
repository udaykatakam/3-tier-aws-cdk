#!/usr/bin/env python3

from aws_cdk import core
from aws_cdk.core import Tag
from 3Tier.stack import MyStack


app = core.App()

stack = MyStack(app, "3Tier-cdk", env={'account': '627796554250', 'region': 'us-west-1'})

core.Tag.add( stack, key='Project Code', value='Project Code')

app.synth()
