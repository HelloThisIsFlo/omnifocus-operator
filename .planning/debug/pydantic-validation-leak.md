---
status: investigating
trigger: "Pydantic validation errors leak raw noise for tags+addTags mutual exclusion and moveTo multiple keys"
created: 2026-03-08T00:00:00Z
updated: 2026-03-08T00:00:00Z
---

## Current Focus

hypothesis: TaskEditSpec.model_validate() in server.py line 232 is not wrapped in try/except -- ValidationError propagates raw to MCP client
test: trace the call path from edit_tasks tool handler through model_validate
expecting: no catch of pydantic.ValidationError anywhere between tool handler and MCP framework
next_action: confirm root cause and identify minimal fix location

## Symptoms

expected: Clean one-liner error messages for all validation failures (like "Tag not found: X")
actual: tags+addTags mutual exclusion and moveTo multiple-key errors return raw Pydantic output with type=value_error, input_value, input_type, URL
errors: Raw Pydantic ValidationError text leaking through MCP responses
reproduction: Call edit_tasks with both tags and addTags, or moveTo with multiple keys
started: Since edit_tasks was implemented

## Eliminated

## Evidence

- timestamp: 2026-03-08T00:01:00Z
  checked: server.py edit_tasks handler (lines 190-234)
  found: Line 232 calls TaskEditSpec.model_validate(items[0]) with NO try/except around it. Same pattern on line 181 for add_tasks.
  implication: Any ValidationError from Pydantic model_validate propagates uncaught to the MCP framework

- timestamp: 2026-03-08T00:02:00Z
  checked: write.py TaskEditSpec._tag_mutual_exclusivity validator (lines 173-184)
  found: Raises ValueError inside a @model_validator. Pydantic wraps this in a ValidationError with all the noisy metadata.
  implication: The clean ValueError message IS there, but Pydantic wraps it before it reaches the tool handler

- timestamp: 2026-03-08T00:03:00Z
  checked: write.py MoveToSpec._exactly_one_key validator (lines 110-119)
  found: Same pattern -- raises ValueError inside @model_validator, Pydantic wraps it in ValidationError
  implication: Both reported symptoms trace to the same root cause

- timestamp: 2026-03-08T00:04:00Z
  checked: service.py edit_task method
  found: No ValidationError catch here either. Service receives already-validated TaskEditSpec. The validation happens BEFORE service is called.
  implication: Fix must be in server.py at the model_validate call sites

## Resolution

root_cause: server.py lines 181 and 232 call model_validate() without catching pydantic.ValidationError. The model validators in write.py raise ValueError (clean messages), but Pydantic wraps these in ValidationError with noisy metadata (type=value_error, input_value, input_type, URL). The MCP framework renders this full ValidationError to the client.
fix: Catch pydantic.ValidationError at both model_validate call sites in server.py and re-raise as ValueError with cleaned message extracted from the ValidationError.
verification:
files_changed: []
