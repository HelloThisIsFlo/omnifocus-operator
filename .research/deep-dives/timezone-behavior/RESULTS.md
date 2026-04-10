# OmniFocus Timezone Behavior — Results

> [One-line summary]

## TL;DR

| Question | Answer |
|----------|--------|
| Q1: Timezone properties on Task? | ... |
| Q2: Can you set floating=false? What changes? | ... |
| Q3: Hidden timezone columns in SQLite? | ... |
| Q4: How does OmniFocus compute effectiveDateDue? | ... |
| Q5: Does conversion hold across DST? | ... |
| Q6: What does OmniFocus store for each date format? | ... |
| Q7: What happens when floating is toggled? | ... |
| Q8: Can you create dates with specific timezones? | ... |

## 1. [Topic]

## 2. [Topic]

## Impact on Codebase

## Deep-Dive References

| Script | What it covers | Link |
|--------|---------------|------|
| 01-tz-api-audit.js | API property audit | [FINDINGS](01-api-audit/FINDINGS.md) |
| 02-date-conversion-proof.py | Conversion formula proof | [FINDINGS](02-conversion-proof/FINDINGS.md) |
| 03-create-and-readback.py | Format normalization | [FINDINGS](03-create-readback/FINDINGS.md) |
| 04-floating-tz-experiment.js | Floating flag behavior | [FINDINGS](04-floating-experiment/FINDINGS.md) |
