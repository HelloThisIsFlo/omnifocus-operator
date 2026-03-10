#!/usr/bin/env bash
# Run RRULE validator spike tests
cd "$(dirname "$0")" && python -m pytest test_rrule_validator.py test_rrule_builder.py -v -o "addopts=" --override-ini="addopts="
