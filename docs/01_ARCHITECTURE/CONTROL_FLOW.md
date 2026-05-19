---
doc_type: architecture
system: Dominion
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - architecture
  - control-flow
  - workflow
---

# Control Flow Architecture

**Purpose:** Control flow patterns for agent workflows, data processing, system initialization.

---

## Agent Workflow Control Flow

```mermaid
flowchart TD
    Start([Agent Session Start]) --> ReadHandoff[Read AGENT_HANDOFF.md]
    ReadHandoff --> InitSession[Agent OS: init_session]
    InitSession --> QueryRAGD{Query RAGD<br/>for context}
    
    QueryRAGD -->|Context loaded| InspectFiles[Inspect files]
    InspectFiles --> UnderstandConstraints[Review safety rules<br/>+ architecture]
    
    UnderstandConstraints --> Plan{Plan approach}
    Plan -->|Simple task| DirectEdit[Make minimal diffs]
    Plan -->|Complex task| Breakdown[Break into subtasks]
    
    Breakdown --> DirectEdit
    DirectEdit --> ValidateLocal{Run tests}
    
    ValidateLocal -->|Fail| Debug[Debug + fix]
    Debug --> DirectEdit
    
    ValidateLocal -->|Pass| TradingCheck{Trading safety check}
    TradingCheck -->|Fail| STOP([STOP<br/>Remove trading code])
    TradingCheck -->|Pass| PlatformHealth{Platform health}
    
    PlatformHealth -->|Warn/Error| Investigate[Investigate issues]
    Investigate --> Fix[Fix if caused by edits]
    Fix --> ValidateLocal
    
    PlatformHealth -->|OK| UpdateDocs[Update docs<br/>if needed]
    UpdateDocs --> RememberRAGD[RAGD remember<br/>key decisions]
    RememberRAGD --> UpdateHandoff[Update AGENT_HANDOFF.md]
    UpdateHandoff --> WriteReport[Write final report]
    WriteReport --> AdversaryReview{Adversary review}
    
    AdversaryReview -->|Toxicity detected| Revise[Revise report]
    Revise --> WriteReport
    
    AdversaryReview -->|Pass| EndSession[Agent OS: end_session]
    EndSession --> End([Session Complete])
```

---

## Data Pipeline Control Flow

```mermaid
flowchart TD
    Start([Pipeline Trigger]) --> CheckSchedule{Scheduled run?}
    CheckSchedule -->|Yes| CheckStaleness[Check last run time]
    CheckSchedule -->|No| ManualRun[Manual CLI run]
    
    CheckStaleness -->|Stale| IngestStart[Begin ingestion]
    CheckStaleness -->|Recent| Skip([Skip run])
    ManualRun --> IngestStart
    
    IngestStart --> ParallelIngest[Parallel fetch:<br/>MT5, Yahoo, FRED, AV, COT]
    
    ParallelIngest --> MT5Data[MT5: Real-time ticks]
    ParallelIngest --> YahooData[Yahoo: GC=F + GLD]
    ParallelIngest --> FREDData[FRED: 10 macro series]
    ParallelIngest --> AVData[Alpha Vantage: GLD]
    ParallelIngest --> COTData[CFTC COT: Positioning]
    
    MT5Data --> CollectSources[Collect all sources]
    YahooData --> CollectSources
    FREDData --> CollectSources
    AVData --> CollectSources
    COTData --> CollectSources
    
    CollectSources --> ValidateSources{Any source failed?}
    ValidateSources -->|All failed| Abort([Abort pipeline])
    ValidateSources -->|Some OK| ProceedFusion[Proceed with available]
    ValidateSources -->|All OK| ProceedFusion
    
    ProceedFusion --> KalmanFusion[6-timescale<br/>Kalman fusion]
    KalmanFusion --> DynamicTrust[Dynamic trust scoring]
    DynamicTrust --> OutlierDetection[Byzantine fault<br/>detection 3σ]
    
    OutlierDetection --> FusedPrice[Fused price estimate<br/>+ uncertainty]
    FusedPrice --> FeatureGen[Generate 400+ features]
    
    FeatureGen --> PriceFeatures[Price features]
    FeatureGen --> MicroFeatures[Microstructure]
    FeatureGen --> CrossAsset[Cross-asset]
    FeatureGen --> COTFeatures[COT features]
    FeatureGen --> MacroFeatures[Macro features]
    FeatureGen --> RegimeFeatures[Regime detection HMM]
    FeatureGen --> CalendarFeatures[Calendar features]
    
    PriceFeatures --> CollectFeatures[Collect features]
    MicroFeatures --> CollectFeatures
    CrossAsset --> CollectFeatures
    COTFeatures --> CollectFeatures
    MacroFeatures --> CollectFeatures
    RegimeFeatures --> CollectFeatures
    CalendarFeatures --> CollectFeatures
    
    CollectFeatures --> HealthMonitor[Health monitoring]
    HealthMonitor --> StalenessCheck{Staleness watchdog}
    StalenessCheck -->|Stale detected| Alert1[Log warning]
    StalenessCheck -->|Fresh| GapCheck{Gap detection}
    
    Alert1 --> GapCheck
    GapCheck -->|Gap detected| Alert2[Log warning]
    GapCheck -->|No gaps| DriftCheck{Drift detection}
    
    Alert2 --> DriftCheck
    DriftCheck -->|Drift detected| Alert3[Log warning]
    DriftCheck -->|No drift| AnomalyCheck{Anomaly detection}
    
    Alert3 --> AnomalyCheck
    AnomalyCheck -->|Anomaly| Alert4[Log warning]
    AnomalyCheck -->|Clean| StoreDuckDB[Write to DuckDB]
    
    Alert4 --> StoreDuckDB
    StoreDuckDB --> GoldMaster[gold_master table]
    StoreDuckDB --> FeaturesTable[features table]
    StoreDuckDB --> IntelReports[intelligence_reports]
    
    GoldMaster --> IngestRAGD[Ingest report to RAGD]
    FeaturesTable --> IngestRAGD
    IntelReports --> IngestRAGD
    
    IngestRAGD --> End([Pipeline Complete])
```

---

## System Initialization Control Flow

```mermaid
flowchart TD
    Start([System Boot]) --> CheckEnv{Environment valid?}
    CheckEnv -->|Missing vars| ConfigError([Exit: Config error])
    CheckEnv -->|OK| CheckDirs{Directories exist?}
    
    CheckDirs -->|Missing| CreateDirs[Create data/, logs/,<br/>backups/, tmp/]
    CheckDirs -->|Exist| CheckRAGD{RAGD daemon running?}
    
    CreateDirs --> CheckRAGD
    CheckRAGD -->|No| StartRAGD[ragd --daemon]
    CheckRAGD -->|Yes| CheckDB{Databases exist?}
    
    StartRAGD --> WaitRAGD[Wait for health check]
    WaitRAGD --> CheckDB
    
    CheckDB -->|Missing| InitDB[Initialize SQLite + DuckDB]
    CheckDB -->|Exist| CheckSchema{Schema current?}
    
    InitDB --> CheckSchema
    CheckSchema -->|Outdated| MigrateSchema[Run migrations]
    CheckSchema -->|Current| CheckTests{Run validation tests?}
    
    MigrateSchema --> CheckTests
    CheckTests -->|--skip-tests| Ready([System Ready])
    CheckTests -->|Default| RunTests[pytest + ctest]
    
    RunTests --> TestResults{All pass?}
    TestResults -->|Fail| TestError([Exit: Tests failed])
    TestResults -->|Pass| TradingCheck{Trading check}
    
    TradingCheck -->|Fail| TradingError([Exit: Trading code detected])
    TradingCheck -->|Pass| Ready
```

---

## CLI Command Control Flow

```mermaid
flowchart TD
    Start([User invokes CLI]) --> ParseCommand{Parse command}
    
    ParseCommand -->|dominion status| StatusCheck[Query RAGD health<br/>+ system stats]
    ParseCommand -->|dominion doctor| DoctorRun[Run health checks]
    ParseCommand -->|dominion search| SearchRAGD[Query RAGD]
    ParseCommand -->|dominion scan| ScanRepo[Scan + index repo]
    ParseCommand -->|dominion vault| VaultOps[Vault operations]
    ParseCommand -->|dominion agent| AgentOps[Agent OS operations]
    ParseCommand -->|Unknown| HelpText([Show help])
    
    StatusCheck --> FormatOutput{--json flag?}
    DoctorRun --> FormatOutput
    SearchRAGD --> FormatOutput
    ScanRepo --> FormatOutput
    VaultOps --> FormatOutput
    AgentOps --> FormatOutput
    
    FormatOutput -->|Yes| OutputJSON[Output JSON]
    FormatOutput -->|No| OutputText[Output formatted text]
    
    OutputJSON --> CheckErrors{Errors occurred?}
    OutputText --> CheckErrors
    
    CheckErrors -->|Yes| ExitError([Exit code 1])
    CheckErrors -->|No| ExitSuccess([Exit code 0])
```

---

## Lock Acquisition Control Flow (Agent OS)

```mermaid
flowchart TD
    Start([Request file lock]) --> CheckSession{Session valid?}
    CheckSession -->|No| SessionError([Error: Invalid session])
    CheckSession -->|Yes| CheckExisting{File locked?}
    
    CheckExisting -->|No| GrantLock[Grant lock<br/>Update lock table]
    CheckExisting -->|Yes, same session| RefreshLock[Refresh lock timestamp]
    CheckExisting -->|Yes, other session| CheckStale{Lock stale?>5min}
    
    CheckStale -->|No| Conflict([Error: Lock conflict])
    CheckStale -->|Yes| StealLock[Steal lock<br/>Log warning]
    
    GrantLock --> LockAcquired([Lock acquired])
    RefreshLock --> LockAcquired
    StealLock --> LockAcquired
```

---

## Retrieval Hints

- "control flow"
- "workflow diagram"
- "agent workflow"
- "pipeline control flow"
- "system initialization"
