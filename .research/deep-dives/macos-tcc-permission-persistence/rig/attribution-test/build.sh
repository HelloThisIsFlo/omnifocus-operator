#!/bin/bash
# Gate 1 build: a launcher .app that SPAWNS a separate reader binary.
# Reuses the same bundle id / display name as the identity test, so we test the
# same identity — only the read now happens in a child process.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/OmniFocus Operator.app"

# the child reader (bare/adhoc — the "python" stand-in)
clang -o "$DIR/of-reader" "$DIR/reader.c"

# the launcher → .app main executable
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
clang -o "$APP/Contents/MacOS/OmniFocusOperatorTest" "$DIR/launcher.c"
cp "$DIR/../Info.plist" "$APP/Contents/Info.plist"

echo "Built:"
echo "  launcher : $APP/Contents/MacOS/OmniFocusOperatorTest"
echo "  reader   : $DIR/of-reader"
echo
echo "Run (via Claude's disclaimer, passing the reader path as the arg):"
echo "  /Applications/Claude.app/Contents/Helpers/disclaimer \"$APP/Contents/MacOS/OmniFocusOperatorTest\" \"$DIR/of-reader\""
