# .ofocus XML Format Reference

> Reverse-engineered from a live OmniFocus 4.7 database (2026-03-06).
> Namespace: `http://www.omnigroup.com/namespace/OmniFocus/v2`

## Bundle Structure

```
OmniFocus.ofocus/                          ← macOS directory (package)
  00000000000000={hash}+{hash}.zip         ← base snapshot (full state)
  YYYYMMDDHHMMSS={prevHash}+{thisHash}.zip ← delta transactions
  data/
    data-{sha256}.zip                      ← content-addressed attachments
  *.capability                             ← format feature declarations
  ../OmniFocus.ofocus-lock                 ← informational lock (plist: host, pid)
```

### Filename Convention

- Timestamps are GMT: `YYYYMMDDHHMMSS`
- Hash chain: `=prevHash+thisHash` links each transaction to its predecessor
- Base file always starts with `00000000000000`
- Sort alphabetically to get chronological order

### Each zip contains exactly one file: `contents.xml`

## Delta Operations

Elements in non-base transactions may have an `op` attribute:

| `op` value | Meaning |
|------------|---------|
| *(absent)* | Insert new element |
| `update` | Partial update — only changed child elements present |
| `delete` | Remove element by ID |
| `reference` | Context snapshot for related elements (informational) |

## Element Types

### `<task>` — Tasks and Projects

```xml
<task id="aM1mzRcLBeV">
  <!-- Project metadata (non-empty = this task IS a project) -->
  <project>
    <folder idref="dhKt78l_09m"/>     <!-- containing folder -->
    <singleton>false</singleton>       <!-- single-action list? -->
    <last-review>2025-12-02T16:07:12.120Z</last-review>
    <next-review>2026-03-10T00:00:00.000Z</next-review>
    <review-interval>~2w</review-interval>  <!-- ~Nw, ~Nm, ~Nd -->
    <status>active</status>            <!-- active|on-hold|done|dropped -->
  </project>

  <!-- Core fields -->
  <inbox>false</inbox>
  <task idref="parentTaskId"/>         <!-- parent task (empty = top-level) -->
  <added order="23">2023-04-17T16:53:42.836Z</added>
  <name>Task name here</name>
  <note>
    <text>
      <p><run><lit>Plain text line</lit></run></p>
      <p><run>
        <style><value key="link">https://example.com</value></style>
        <lit>Link text</lit>
      </run></p>
    </text>
  </note>
  <rank>1073741821</rank>              <!-- sort order within parent -->
  <hidden/>                            <!-- present = hidden by defer date -->

  <!-- Dates (ISO 8601, with .NNN milliseconds, no timezone = floating) -->
  <start>2026-03-12T08:00:00.000</start>    <!-- defer date -->
  <due>2026-03-15T19:00:00.000</due>
  <planned>2026-03-14T10:00:00.000</planned> <!-- OF 4.7+ -->
  <completed>2026-03-13T14:22:00.000Z</completed>

  <!-- Properties -->
  <estimated-minutes>30</estimated-minutes>
  <order>parallel</order>              <!-- parallel|sequential -->
  <flagged>false</flagged>
  <completed-by-children>false</completed-by-children>

  <!-- Repetition (iCal RRULE format) -->
  <repetition-rule>FREQ=WEEKLY;INTERVAL=3;BYDAY=TH</repetition-rule>
  <repetition-method>start-after-completion</repetition-method>
  <!-- OF 4.7+ additions: -->
  <repetition-schedule-type/>          <!-- Regularly|FromCompletion|None -->
  <repetition-anchor-date/>            <!-- DueDate|DeferDate|PlannedDate -->
  <catch-up-automatically>false</catch-up-automatically>
  <next-clone-identifier>43</next-clone-identifier>

  <!-- Alarm policies -->
  <due-date-alarm-policy/>
  <defer-date-alarm-policy/>
  <latest-time-to-start-alarm-policy/>
  <planned-date-alarm-policy/>         <!-- OF 4.7+ -->

  <modified>2026-02-16T17:54:02.456Z</modified>
</task>
```

### `<folder>` — Folders

```xml
<folder id="mlY2NLUV431">
  <folder idref="oeANn6-qhvS"/>       <!-- parent folder (empty = top-level) -->
  <added>2023-04-17T16:47:36.626Z</added>
  <name>Career | Software</name>
  <note/>
  <rank>-1811939328</rank>
  <hidden/>
  <modified>2026-01-06T16:02:05.641Z</modified>
</folder>
```

### `<context>` — Tags (legacy XML name)

```xml
<context id="gjwhx2rw8p9">
  <context/>                            <!-- parent tag (empty = top-level) -->
  <added order="6">2023-04-17T16:48:46.011Z</added>
  <name>Someday</name>
  <note/>
  <rank>1263225674</rank>
  <hidden/>
  <prohibits-next-action>true</prohibits-next-action>  <!-- = "on hold" tag -->
  <location/>
  <tasks-user-ordered>false</tasks-user-ordered>
  <modified>2023-04-17T17:20:08.270Z</modified>
</context>
```

### `<task-to-tag>` — Task-Tag Links

```xml
<task-to-tag id="eT0g7xNOI2_.iidsEaNQdcF">
  <added order="64">2023-04-17T16:48:46.011Z</added>
  <task idref="eT0g7xNOI2_"/>
  <context idref="iidsEaNQdcF"/>
  <rank-in-task>0001</rank-in-task>    <!-- tag ordering on this task -->
  <rank-in-tag/>
</task-to-tag>
```

### `<perspective>` — Perspectives

```xml
<perspective id="ProcessRecentChanges">
  <added>2023-04-17T16:46:25.135Z</added>
  <plist version="1.0">
    <dict>
      <key>name</key>
      <string>Changed</string>
      <key>filterRules</key>
      <string>[{"disabledRule":{"actionAvailability":"remaining"}}]</string>
      <key>viewState</key>
      <dict>...</dict>
    </dict>
  </plist>
  <icon-attachment/>
  <modified>2026-02-18T13:25:42.396Z</modified>
</perspective>
```

### `<setting>` — App Settings

```xml
<setting id="DueSoonInterval">
  <added>2023-04-17T16:47:18.155Z</added>
  <plist version="1.0"><integer>86400</integer></plist>
  <modified>2024-12-04T10:21:39.216Z</modified>
</setting>
```

Key settings: `DueSoonInterval` (seconds), `DefaultStartTime`, `DefaultDueTime`,
`OFMCompleteWhenLastItemComplete`, `_ForecastBlessedTagIdentifier`.

### `<alarm>` — Notifications

```xml
<alarm id="l14gtDERXnJ">
  <added>2024-09-30T09:18:47.749Z</added>
  <task idref="ekJ4f134dIZ"/>
  <kind>due-relative</kind>           <!-- absolute|due-relative -->
  <variant/>                           <!-- snoozed|'' -->
  <fire-date/>
  <fire-offset>-3600</fire-offset>    <!-- seconds before due -->
  <repeat-interval>0</repeat-interval>
</alarm>
```

## ID Format

- 11-character strings using a base64-like alphabet: `a-z`, `A-Z`, `0-9`, `-`, `_`
- Example: `aM1mzRcLBeV`, `djJA1ZB2YFr`

## Date Formats

- ISO 8601 with milliseconds: `2026-03-06T11:31:04.339Z`
- No timezone suffix = floating time (interpreted in user's local timezone)
- `Z` suffix = UTC

## Capability Files

`.capability` files declare format features the database uses. Present in test DB:
- `active_object_hidden_dates.capability`
- `delta_transactions.capability`
- `external_attachments.capability`
- `floating_time_zones.capability`
- `stable_repeats.capability`
- `unknown_element_import.capability`
- `v4_7_features.capability`
- `versioned_perspectives.capability`
