-- OmniFocus 4 SQLite Cache Schema
-- Extracted from: ~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/
--   com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db
-- Date: 2026-03-06
-- NOTE: This is an internal cache, NOT the source of truth (.ofocus XML is).
--       Path and schema may change between OmniFocus versions.

-- Task table (includes project-tasks)
-- Key insight: has independent boolean columns for blocked/overdue/dueSoon
-- (unlike the bridge's single-winner taskStatus enum)
CREATE TABLE Task (
    persistentIdentifier                TEXT PRIMARY KEY,
    name                                TEXT,
    plainTextNote                       TEXT,
    noteXMLData                         BLOB,
    parent                              TEXT,  -- parent task ID
    projectInfo                         TEXT,  -- FK to ProjectInfo.pk (NULL for non-projects)
    containingProjectInfo               TEXT,  -- FK to ProjectInfo.pk (containing project)
    rank                                INTEGER,
    creationOrdinal                     INTEGER,

    -- Dates (Core Foundation absolute time: seconds since 2001-01-01)
    dateAdded                           TIMESTAMP,
    dateModified                        TIMESTAMP,
    dateCompleted                       TIMESTAMP,
    dateDue                             DATETIME,
    dateToStart                         DATETIME,  -- defer date
    datePlanned                         DATETIME,
    dateHidden                          TIMESTAMP,

    -- Pre-computed effective dates (inherited from parent chain)
    effectiveDateDue                    TIMESTAMP,
    effectiveDateToStart                TIMESTAMP,
    effectiveDateCompleted              TIMESTAMP,
    effectiveDatePlanned                TIMESTAMP,
    effectiveDateHidden                 TIMESTAMP,

    -- Boolean flags
    flagged                             INTEGER,
    effectiveFlagged                    INTEGER,
    sequential                          INTEGER,
    inInbox                             INTEGER,
    effectiveInInbox                    INTEGER,

    -- Pre-computed status booleans (independent, not mutually exclusive!)
    blocked                             INTEGER,
    blockedByFutureStartDate            INTEGER,
    dueSoon                             INTEGER,
    overdue                             INTEGER,

    -- Children counts
    childrenCount                       INTEGER,
    childrenCountActive                 INTEGER,
    childrenCountAvailable              INTEGER,
    childrenCountCompleted              INTEGER,
    childrenState                       INTEGER,
    completeWhenChildrenComplete        INTEGER,

    -- Project containment
    containingProjectContainsSingletons INTEGER,
    effectiveContainingProjectInfoActive    INTEGER,
    effectiveContainingProjectInfoRemaining INTEGER,
    containsNextTask                    INTEGER,
    nextTaskOfProjectInfo               TEXT,

    -- Estimation
    estimatedMinutes                    INTEGER,
    maximumEstimateInTree               INTEGER,
    minimumEstimateInTree               INTEGER,
    hasUnestimatedLeafTaskInTree        INTEGER,

    -- Repetition
    repetitionRuleString                TEXT,
    repetitionScheduleTypeString        TEXT,
    repetitionAnchorDateKey             TEXT,
    catchUpAutomatically                INTEGER,

    -- Misc
    tagged                              INTEGER,
    hasCompletedDescendant              INTEGER,
    hasFlaggedTaskInTree                INTEGER,
    nextCloneIdentifier                 INTEGER,
    sharedPlanObjectId                  INTEGER,

    -- Alarm policies
    deferDateAlarmPolicyString          TEXT,
    dueDateAlarmPolicyString            TEXT,
    latestTimeToStartAlarmPolicyString  TEXT,
    plannedDateAlarmPolicyString        TEXT
);

CREATE TABLE ProjectInfo (
    pk                  TEXT PRIMARY KEY,
    task                TEXT,  -- FK to Task.persistentIdentifier
    folder              TEXT,  -- FK to Folder.persistentIdentifier
    status              TEXT,  -- 'active', 'inactive' (on-hold), 'done', 'dropped'
    containsSingletonActions INTEGER,
    lastReviewDate      TIMESTAMP,
    nextReviewDate      TIMESTAMP,
    reviewRepetitionString TEXT,
    nextTask            TEXT   -- FK to Task.persistentIdentifier
);

CREATE TABLE Folder (
    persistentIdentifier TEXT PRIMARY KEY,
    name                TEXT,
    parent              TEXT,  -- FK to Folder.persistentIdentifier
    rank                INTEGER,
    dateAdded           TIMESTAMP,
    dateModified        TIMESTAMP,
    active              INTEGER,
    childrenCount       INTEGER,
    -- note: 'hidden' not directly stored, computed from 'active'
    noteXMLData         BLOB
);

CREATE TABLE Context (  -- "Tags" in the UI
    persistentIdentifier TEXT PRIMARY KEY,
    name                TEXT,
    parent              TEXT,  -- FK to Context.persistentIdentifier
    rank                INTEGER,
    dateAdded           TIMESTAMP,
    dateModified        TIMESTAMP,
    active              INTEGER,
    allowsNextAction    INTEGER,
    childrenCount       INTEGER,
    availableTaskCount  INTEGER,
    remainingTaskCount  INTEGER,
    noteXMLData         BLOB
);

CREATE TABLE TaskToTag (
    persistentIdentifier TEXT PRIMARY KEY,
    task                TEXT,  -- FK to Task.persistentIdentifier
    tag                 TEXT,  -- FK to Context.persistentIdentifier
    rankInTask          TEXT,
    rankInTag           TEXT,
    dateAdded           TIMESTAMP
);

CREATE TABLE Perspective (
    persistentIdentifier TEXT PRIMARY KEY,
    dateAdded           TIMESTAMP,
    dateModified        TIMESTAMP,
    valueData           BLOB  -- plist containing name, filterRules, viewState, etc.
);

CREATE TABLE Setting (
    persistentIdentifier TEXT PRIMARY KEY,
    dateAdded           TIMESTAMP,
    dateModified        TIMESTAMP,
    valueData           BLOB  -- plist value
);

CREATE TABLE Alarm (
    persistentIdentifier TEXT PRIMARY KEY,
    task                TEXT,
    dateAdded           TIMESTAMP,
    kind                TEXT,
    variant             TEXT,
    fireDate            DATETIME,
    fireOffset          INTEGER,
    repeatInterval      INTEGER
);

CREATE TABLE Attachment (
    persistentIdentifier TEXT PRIMARY KEY,
    task                TEXT,
    dateAdded           TIMESTAMP,
    name                TEXT
);

CREATE TABLE Team (
    persistentIdentifier TEXT PRIMARY KEY
    -- empty in personal databases
);

CREATE TABLE ODOMetadata (
    key   TEXT PRIMARY KEY,
    value TEXT
);
