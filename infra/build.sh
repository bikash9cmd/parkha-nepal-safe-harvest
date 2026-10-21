#!/usr/bin/env bash
# Assembles the Lambda package: the code, the label tables and the advisory notes, nothing else.
# The data ships inside the package on purpose (ADR-006): a ban-list change is a deploy, and a
# deploy runs the evaluation in CI first.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf build/lambda && mkdir -p build/lambda
cp -r parkha data corpus build/lambda/
cp requirements-lambda.txt build/lambda/requirements.txt
find build/lambda -name __pycache__ -type d -prune -exec rm -rf {} +
du -sh build/lambda
