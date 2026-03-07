#!/usr/bin/env bash
# Tail a log file, filtering for omnifocus-operator lines
tail -f "$1" | grep --line-buffered "omnifocus-operator"
