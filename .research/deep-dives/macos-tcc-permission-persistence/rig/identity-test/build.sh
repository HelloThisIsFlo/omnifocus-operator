#!/bin/bash
# Builds "OmniFocus Operator.app" wrapping trigger.c.
# Default clang output is adhoc-signed = Round A (control, no real identity).
# To run Round B: re-sign with codesign --sign "<cert>" after building.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/OmniFocus Operator.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
clang -o "$APP/Contents/MacOS/OmniFocusOperatorTest" "$DIR/trigger.c"
cp "$DIR/../Info.plist" "$APP/Contents/Info.plist"

echo "Built: $APP"
echo "Launch target: $APP/Contents/MacOS/OmniFocusOperatorTest"
