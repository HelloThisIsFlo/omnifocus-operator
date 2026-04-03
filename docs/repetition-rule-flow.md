# Repetition Rule Flow — Current Architecture

## Write Path: Add Pipeline

```mermaid
flowchart TD
    subgraph MCP["MCP Server"]
        A["Agent sends add_tasks JSON"]
    end

    subgraph Contracts["contracts/"]
        CMD["AddTaskCommand"]
        SPEC["RepetitionRuleAddSpec"]
        S1["├─ frequency: <b>FrequencyAddSpec</b>"]
        S2["├─ schedule: Schedule"]
        S3["├─ based_on: BasedOn"]
        S4["└─ end: <b>EndConditionSpec</b> | None"]
    end

    subgraph Service["service/ — _AddTaskPipeline"]
        CONV["<b>convert.py</b><br/><code>frequency_from_spec()</code><br/><code>end_condition_from_spec()</code>"]
        FREQ["self._frequency: <b>Frequency</b>"]
        END_C["self._end_condition: <b>EndCondition</b>"]
        NORM["domain.normalize_empty_specialization_fields()"]
        BUILD["Construct <b>RepetitionRuleRepoPayload</b><br/>(frequency, schedule, based_on, end)<br/><i>all core types</i>"]
        SLOT["payload.build_add() — slots it in"]
    end

    subgraph RepoPayload["RepetitionRuleRepoPayload<br/><i>(pure data carrier)</i>"]
        RP_F["frequency: Frequency"]
        RP_S["schedule: Schedule"]
        RP_B["based_on: BasedOn"]
        RP_E["end: EndCondition | None"]
    end

    subgraph Repository["repository/"]
        DUMP["bridge_write_mixin._dump_payload()"]
        SER["<b>rrule/serialize.py</b><br/><code>serialize_repetition_rule()</code>"]
        RRULE["rrule/builder.py → RRULE string"]
        SCHED["rrule/schedule.py → bridge enums"]
        BRIDGE_FMT["{<br/>  ruleString: 'FREQ=WEEKLY;...',<br/>  scheduleType: 'fixed',<br/>  anchorDateKey: 'due',<br/>  catchUpAutomatically: true<br/>}"]
        BRIDGE["Bridge.send_command()"]
    end

    A --> CMD --> SPEC --> S1 & S2 & S3 & S4
    CMD =="spec types"==> CONV
    CONV -->|"FrequencyAddSpec → Frequency"| FREQ
    CONV -->|"EndConditionSpec → EndCondition"| END_C
    FREQ --> NORM --> FREQ
    FREQ & END_C ==> BUILD
    BUILD --> SLOT

    SLOT =="RepoPayload<br/>(core types)"==> DUMP
    DUMP --> SER
    SER --> RRULE & SCHED
    RRULE & SCHED --> BRIDGE_FMT
    BRIDGE_FMT --> BRIDGE

    style MCP fill:#fafafa,stroke:#bdbdbd
    style Contracts fill:#fff8f0,stroke:#e65100
    style Service fill:#e0f2f1,stroke:#00897b
    style RepoPayload fill:#e8f0fe,stroke:#1565c0
    style Repository fill:#efebe9,stroke:#795548
    style CONV fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style FREQ fill:#e3f2fd,stroke:#1565c0
    style END_C fill:#e3f2fd,stroke:#1565c0
    style BUILD fill:#e3f2fd,stroke:#1565c0
    style SER fill:#dce8d4,stroke:#558b2f,stroke-width:2px
    style BRIDGE_FMT fill:#f5f5f5,stroke:#9e9e9e
    style SLOT fill:#f5f5f5,stroke:#9e9e9e
    style S1 fill:#fff3e0,stroke:#e65100
    style S4 fill:#fff3e0,stroke:#e65100
```

## Write Path: Edit Pipeline

```mermaid
flowchart TD
    subgraph Contracts["contracts/"]
        CMD["EditTaskCommand"]
        SPEC["RepetitionRuleEditSpec"]
        S1["├─ frequency: <b>FrequencyEditSpec</b> | UNSET"]
        S2["├─ schedule: Schedule | UNSET"]
        S3["├─ based_on: BasedOn | UNSET"]
        S4["└─ end: <b>EndConditionSpec</b> | None | UNSET"]
    end

    subgraph Service["service/ — _EditTaskPipeline._apply_repetition_rule()"]
        subgraph Resolve["① Resolve — <code>_resolve_repetition_fields()</code>"]
            subgraph EndResolve["End condition"]
                E1{"is_set(spec.end)?"}
                E_CONV["end_condition_from_spec()"]
                E_EXIST["existing.end <i>(already core)</i>"]
                E_NONE["None"]
            end

            subgraph FreqResolve["Frequency — <code>_resolve_frequency()</code>"]
                F1{"is_set(spec.frequency)?"}
                F_MERGE["_merge_frequency → Frequency"]
                F_BUILD["_build_from_edit_spec → Frequency"]
                F_EXIST["existing.frequency <i>(already core)</i>"]
            end
        end

        subgraph NormWarn["② Normalize + Warn — <code>_normalize_and_warn_repetition()</code>"]
            NORM["domain.normalize_empty_specialization_fields()"]
            WARN["domain.check_repetition_warnings()"]
            ANCHOR["domain.check_anchor_date_warning()"]
        end

        subgraph Assemble["③ Assemble — <code>_assemble_repetition_payload()</code>"]
            BUILD["Construct <b>RepetitionRuleRepoPayload</b><br/>(frequency, schedule, based_on, end)"]
            NOOP["No-op detection"]
        end
    end

    subgraph Repository["repository/"]
        DUMP["bridge_write_mixin._dump_payload()"]
        SER["<b>rrule/serialize.py</b><br/><code>serialize_repetition_rule()</code>"]
        RRULE["rrule/builder.py → RRULE string"]
        SCHED["rrule/schedule.py → bridge enums"]
        BRIDGE_FMT["{<br/>  ruleString: 'FREQ=WEEKLY;...',<br/>  scheduleType: 'fixed',<br/>  anchorDateKey: 'due',<br/>  catchUpAutomatically: true<br/>}"]
        BRIDGE["Bridge.send_command()"]
    end

    CMD --> SPEC --> S1 & S2 & S3 & S4
    SPEC --> E1 & F1

    E1 -->|"Yes"| E_CONV
    E1 -->|"No, existing"| E_EXIST
    E1 -->|"No, none"| E_NONE

    F1 -->|"Same type"| F_MERGE
    F1 -->|"Type change"| F_BUILD
    F1 -->|"Not set"| F_EXIST

    F_MERGE & F_BUILD & F_EXIST --> NORM
    E_CONV & E_EXIST & E_NONE --> NORM
    NORM --> WARN --> ANCHOR

    ANCHOR --> BUILD --> NOOP
    NOOP =="RepetitionRuleRepoPayload<br/>(core types)"==> DUMP
    DUMP --> SER
    SER --> RRULE & SCHED
    RRULE & SCHED --> BRIDGE_FMT
    BRIDGE_FMT --> BRIDGE

    style Contracts fill:#fff8f0,stroke:#e65100
    style Service fill:#e0f2f1,stroke:#00897b
    style Repository fill:#efebe9,stroke:#795548
    style Resolve fill:#e8f5e920,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5
    style NormWarn fill:#e3f2fd20,stroke:#1565c0,stroke-width:2px,stroke-dasharray: 5 5
    style Assemble fill:#e3f2fd20,stroke:#1565c0,stroke-width:2px,stroke-dasharray: 5 5
    style E_CONV fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style BUILD fill:#e3f2fd,stroke:#1565c0
    style NOOP fill:#f5f5f5,stroke:#9e9e9e
    style SER fill:#dce8d4,stroke:#558b2f,stroke-width:2px
    style BRIDGE_FMT fill:#f5f5f5,stroke:#9e9e9e
    style DUMP fill:#f5f5f5,stroke:#9e9e9e
    style S1 fill:#fff3e0,stroke:#e65100
    style S4 fill:#fff3e0,stroke:#e65100
```

## Read Path

The mirror image of the write paths above. The same `repository/rrule/` package that serializes core types to RRULE on writes also parses RRULE back to core types on reads. Both read implementations (hybrid SQLite, bridge-only adapter) converge on the same `rrule/` functions.

```mermaid
flowchart TD
    subgraph OmniFocus["OmniFocus / SQLite"]
        RAW["{<br/>  ruleString: 'FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2;COUNT=12',<br/>  scheduleType: 'fixed',<br/>  anchorDateKey: 'dateDue',<br/>  catchUpAutomatically: true<br/>}"]
    end

    subgraph Repository["repository/"]
        ENTRY["<b>hybrid.py</b> <code>_build_repetition_rule()</code><br/><b>adapter.py</b> <code>_adapt_repetition_rule()</code><br/><i>normalize raw fields → common shape via mapping tables</i>"]
        FREQ["<b>rrule/parser.py</b><br/><code>parse_rrule(ruleString)</code><br/>→ <b>Frequency</b>(type='monthly', interval=1,<br/>    on=OrdinalWeekday(second='weekday'))"]
        END_C["<b>rrule/parser.py</b><br/><code>parse_end_condition(ruleString)</code><br/>→ <b>EndByOccurrences</b>(12)"]
        SCHED["<b>rrule/schedule.py</b><br/><code>derive_schedule(scheduleType, catchUp)</code><br/>→ <b>Schedule</b>.REGULARLY_WITH_CATCH_UP"]
        ANCHOR["anchorDateKey mapping<br/>→ <b>BasedOn</b>.DUE_DATE"]
        CORE["<b>RepetitionRule</b><br/>├─ frequency: <b>Frequency</b>(type='monthly', interval=1,<br/>│    on=OrdinalWeekday(second='weekday'))<br/>├─ schedule: <b>Schedule</b>.REGULARLY_WITH_CATCH_UP<br/>├─ based_on: <b>BasedOn</b>.DUE_DATE<br/>└─ end: <b>EndByOccurrences</b>(12)"]
    end

    subgraph Service["service/"]
        SVC["Works with core types directly<br/><i>No RRULE knowledge needed</i>"]
    end

    subgraph MCP["MCP Server"]
        AGENT["Agent receives structured data"]
    end

    RAW ==> ENTRY
    ENTRY --> FREQ
    ENTRY --> END_C
    ENTRY --> SCHED --> ANCHOR
    FREQ & END_C & ANCHOR ==> CORE
    CORE ==> SVC ==> AGENT

    style OmniFocus fill:#fafafa,stroke:#bdbdbd
    style Repository fill:#efebe9,stroke:#795548
    style Service fill:#e0f2f1,stroke:#00897b
    style MCP fill:#fafafa,stroke:#bdbdbd
    style ENTRY fill:#f5f5f5,stroke:#9e9e9e
    style RAW fill:#f5f5f5,stroke:#9e9e9e
    style FREQ fill:#dce8d4,stroke:#558b2f,stroke-width:2px
    style END_C fill:#dce8d4,stroke:#558b2f,stroke-width:2px
    style SCHED fill:#dce8d4,stroke:#558b2f,stroke-width:2px
    style ANCHOR fill:#dce8d4,stroke:#558b2f
    style CORE fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style SVC fill:#f5f5f5,stroke:#9e9e9e
```

## Package Structure

```mermaid
flowchart TD
    subgraph service["service/"]
        convert["convert.py<br/><i>spec → core</i>"]
        domain["domain.py<br/><i>business rules</i>"]
        payload["payload.py<br/><i>mechanical assembly</i>"]
        svc["service.py<br/><i>pipeline orchestration</i>"]
    end

    subgraph repository["repository/"]
        subgraph rrule["rrule/"]
            parser["parser.py — RRULE → Frequency"]
            builder["builder.py — Frequency → RRULE"]
            schedule["schedule.py — enum mappings"]
            serialize["serialize.py — full payload serialization"]
        end
        mixin["bridge_write_mixin.py<br/><code>_dump_payload()</code>"]
        subgraph hybrid["hybrid/"]
            hyb["hybrid.py — reads: calls parser"]
        end
        subgraph bridge_only["bridge_only/"]
            bo["bridge_only.py"]
            adapter["adapter.py — reads: calls parser"]
        end
    end

    svc --> convert
    svc --> domain
    svc --> payload
    mixin --> serialize
    serialize --> builder & schedule
    hyb --> parser & schedule
    adapter --> parser & schedule

    style service fill:#e0f2f1,stroke:#00897b,stroke-dasharray: 5 5
    style repository fill:#efebe9,stroke:#795548,stroke-dasharray: 5 5
    style rrule fill:#dce8d4,stroke:#558b2f
    style convert fill:#e8f5e9,stroke:#2e7d32
    style payload fill:#f5f5f5,stroke:#9e9e9e
```

## Color Legend

| Color | Meaning |
|-------|---------|
| **Orange** | Spec types (contract layer, write-side input) |
| **Blue** | Core types (model layer, domain truth) |
| **Green** | Service-layer conversion (spec → core) |
| **Sage** | Repository-layer translation (core ↔ RRULE/bridge format) |
| **Grey** | Mechanical / pass-through (no transformation) |

### Subgraph Backgrounds

Consistent across all diagrams — the background tint identifies the architectural layer:

| Background | Layer |
|------------|-------|
| Light orange | `contracts/` |
| Light teal | `service/` |
| Warm tan | `repository/` |
| Light blue | Core type carriers (RepoPayload) |
| Neutral grey | External boundaries (MCP Server, OmniFocus) |
