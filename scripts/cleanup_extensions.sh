#!/usr/bin/env bash
set -e
echo "🧹 Removing 37 unused Antigravity extensions..."
antigravity --uninstall-extension redhat.java
antigravity --uninstall-extension oracle.oracle-java
antigravity --uninstall-extension broadcommfd.debugger-for-mainframe
antigravity --uninstall-extension google.geminicodeassist
antigravity --uninstall-extension openai.chatgpt
echo "✅ Done! Restart Antigravity."
