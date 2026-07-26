# Graph Report - C:\Users\andre\AppData\Local\Temp\claude\repos\Alfred  (2026-07-26)

## Corpus Check
- Large corpus: 306 files · ~523,624 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 2676 nodes · 6528 edges · 129 communities (118 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 259 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117

## God Nodes (most connected - your core abstractions)
1. `el()` - 55 edges
2. `runHook()` - 32 edges
3. `setLiveState()` - 29 edges
4. `detectHtml()` - 28 edges
5. `initGlobalBar()` - 28 edges
6. `collectBrowserFindings()` - 26 edges
7. `buildInsertConfigureRow()` - 26 edges
8. `handleKeyDown()` - 26 edges
9. `showToast()` - 25 edges
10. `resumeSession()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `skills/agent-task-decomposition.md` --semantically_similar_to--> `context-engineering technique`  [INFERRED] [semantically similar]
  memory/learning-log.md → requirements/discovered-tools.md
- `powerbi-modeling MCP tool` --semantically_similar_to--> `powerbi-modeling-mcp server`  [INFERRED] [semantically similar]
  agents/dlp-doctor.md → requirements/mcp-tools.md
- `DLP Doctor hard rules (never edit Gen1 dataflow, clean temp tables)` --semantically_similar_to--> `Forbidden auth rule (no device-code auth for agent actions)`  [INFERRED] [semantically similar]
  agents/dlp-doctor.md → requirements/safety-gates.md
- `Install-Tool()` --calls--> `Find-Command()`  [INFERRED]
  Alfred-Install.ps1 → Alfred-Common.ps1
- `Install-Uv()` --calls--> `Find-Command()`  [INFERRED]
  Alfred-Install.ps1 → Alfred-Common.ps1

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Alfred provisioning flow (setup -> provision -> update)** — setup_ps1, provision_cursor_ps1, run_alfred_bat, check_updates_ps1, backend_cli_py [EXTRACTED 0.90]
- **DLP Tool v2.0 medallion dataflow lineage (Bronze -> Silver FactPlan/Dimensions -> Audit)** — df_bronze_plans, df_silver_factplan, df_silver_dimensions, df_silver_audit, dlp_tool_v2_dashboard [EXTRACTED 0.90]
- **Destructive-tool safety governance across manifests** — requirements_safety_gates_md, alfred_tools_json, requirements_mcp_tools_md, agents_md_alfred_specific_rules [INFERRED 0.85]

## Communities (129 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (126): acceptedDomAlreadyClean(), addManualContextText(), applyPlaceholderSizingStyles(), applySvelteComponentVariantStyle(), bufferToBase64(), buildCollapsible(), buildColorModels(), buildListHtml() (+118 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (84): borderColorsFromStyle(), borderWidthsFromStyle(), checkClippedOverflow(), checkCreamPalette(), checkElementClippedOverflow(), checkElementClippedOverflowDOM(), checkElementGptBorderShadow(), checkElementGptBorderShadowDOM() (+76 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (58): confirm(), detectCli(), formatFindings(), formatFindingSummary(), handleStdin(), printUsage(), createBrowserDetector(), detectUrl() (+50 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (68): addBrowserFindings(), addVisualContrastFindings(), addVisualContrastResult(), analyzeVisualContrast(), analyzeVisualContrastCandidate(), blendRgba(), browserColorsClose(), browserDesignSystemConfig() (+60 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (69): abortSvelteComponentInjection(), applyEditing(), buildLocatorForLeaf(), buildPickedAnchorSnapshot(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), cleanup() (+61 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (62): applyOriginalAttrsToSvelteAnchor(), applySavedSessionMeta(), buildInsertPlaceholderSnapshotFromDom(), checkpointPayload(), clampVariantIndex(), clearHandled(), commitAcceptedSvelteComponentToDom(), elementMatchesOriginalMarkup() (+54 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (56): applyGlobalBarLabelState(), armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), clearSteerAwaitTimer(), clearSteerFocusRecoverTimer(), collapsePageChat() (+48 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (52): ae(), be(), bt(), Ce(), Ct(), de(), dt(), _e() (+44 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (51): addColorObject(), addDesignColor(), addRoundedScale(), addRoundedToken(), addSidecarColors(), addSidecarRadii(), addTypographyFonts(), canonicalDesignFindingKey() (+43 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (48): detectCsp(), INLINE_HEADER_SIGNALS, LAYOUT_EXTS, MONOREPO_HELPER_SIGNALS, NUXT_ROUTE_RULES_SIGNALS, NUXT_SECURITY_SIGNALS, SCAN_EXTS, SKIP_DIRS (+40 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (49): allEntryIds(), argVal(), buildRepairBatch(), candidatesForEntry(), changedFilesSinceSnapshot(), clearAppliedEntries(), collectApplyOwnedFiles(), collectRollbackFiles() (+41 more)

### Community 11 - "Community 11"
Cohesion: 0.10
Nodes (47): applyDetectionConfigSource(), clampByte(), cleanIgnoreValueDisplay(), cloneDetectionConfig(), cloneRawDetectionConfig(), colorIgnoreKey(), DEFAULT_DETECTION_CONFIG, DETECTOR_CONFIG_KEYS (+39 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (46): #000000, #0072B2, #009E73, #56B4E9, #CC79A7, #D55E00, #E69F00, #F0E442 (+38 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (45): ACK_EXTS, applyConfigSource(), applyDetectorConfigSource(), applyPatchText(), clampByte(), cloneDefaultConfig(), CO_SCAN_STYLE_NAMES, colorIgnoreKey() (+37 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (47): actionLabel(), applyConfigureBarChrome(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow() (+39 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (42): addOpToManualApplyChunk(), APPLY_EVENT_HARD_TIMEOUT_MS, APPLY_EVENT_SOFT_DEADLINE_MS, buildManualApplyAgentAction(), clearManualApplyTransaction(), collectManualApplyFiles(), compactManualApplyBatch(), compactManualApplyCandidates() (+34 more)

### Community 16 - "Community 16"
Cohesion: 0.10
Nodes (44): applyLegacyDeferredAcceptsOnStartup(), appendCssToSvelteStyle(), appendSanitizedCssRule(), applyDeferredSvelteComponentAccepts(), bakeParamValuesInCss(), buildInsertVariantStub(), buildPropContract(), buildPropsScript() (+36 more)

### Community 17 - "Community 17"
Cohesion: 0.10
Nodes (30): applyStaticDeclaration(), buildBorderOverrideMap(), buildStaticStyleMap(), buildStaticWindow(), collectStaticCssRules(), compareStaticPriority(), cssPropToCamel(), expandStaticBoxValues() (+22 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (39): ACTIONS, addIgnoreFile(), addIgnoreRule(), addIgnoreValue(), DETECTOR_CONFIG_KEYS, detectorSection(), fileHasImpeccableHookMarker(), HOOK_MANIFEST_TARGETS (+31 more)

### Community 19 - "Community 19"
Cohesion: 0.11
Nodes (39): allow(), bumpCursorDenial(), cursorBlockMessage(), deny(), done(), escapeRegExp(), findingSignature(), firstMatch() (+31 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (37): acknowledgePendingEvent(), activeSessionSummaries(), agentPollingConnected(), annotRoot, args, broadcast(), broadcastAgentPollingIfChanged(), cancelQueuedAnonymousExitEvents() (+29 more)

### Community 21 - "Community 21"
Cohesion: 0.09
Nodes (34): checkBorders(), checkClippedOverflow(), checkElementBorders(), checkElementBordersDOM(), checkElementClippedOverflow(), checkElementClippedOverflowDOM(), checkElementItalicSerif(), checkElementItalicSerifDOM() (+26 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (33): Add-HookEntry(), Convert-AgentMdToCodexToml(), Expand-EnvPlaceholders(), Get-AlfredKnownServerNames(), Install-ThirdPartyAgentSkills(), Invoke-McpCliAdd(), Invoke-NpxBackgroundJob(), Invoke-ProjectSeed() (+25 more)

### Community 23 - "Community 23"
Cohesion: 0.08
Nodes (22): FORBIDDEN_MANUAL_EDIT_TEXT_CHARS, INSERT_POSITIONS, isValidId(), isValidVariantId(), validateAnnotationFields(), validateEvent(), validateInsertGenerate(), validateManualEditEvent() (+14 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (35): argVal(), buildInsertWrapperLines(), computeInsertLine(), INSERT_POSITIONS, insertCli(), isInsertPosition(), resolveElementMatch(), buildSvelteComponentCssAuthoring() (+27 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (36): context7, duckdb, excel, excel-mcp, fal-ai, fetch, filesystem, firecrawl (+28 more)

### Community 26 - "Community 26"
Cohesion: 0.15
Nodes (33): buildColor(), CANONICAL_SECTIONS, collectBullets(), collectColorValues(), collectParagraphs(), detectFormat(), extractColors(), extractComponents() (+25 more)

### Community 27 - "Community 27"
Cohesion: 0.14
Nodes (32): acceptCli(), argVal(), buildCarbonizeReplacement(), decodeHtmlAttr(), deindentContent(), detectCommentSyntax(), escapeRegExp(), expandReplaceRange() (+24 more)

### Community 28 - "Community 28"
Cohesion: 0.14
Nodes (31): applyMockWrites(), buildCopyEditBatchPrompt(), checkFrameworkSourceSyntax(), chooseCopyEditAgent(), COMMAND_AUTH_CACHE, commandAuthed(), commandExists(), compactBatchForPrompt() (+23 more)

### Community 29 - "Community 29"
Cohesion: 0.11
Nodes (31): barPaletteForTheme(), brandMarkSvg(), buildDesignHeader(), buildParamsPanel(), designPanelCss(), detectPageTheme(), ensureAgentPollTooltip(), fetchAgentPollingStatus() (+23 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (29): .cursor/rules/00-agent-tooling.mdc, context7 MCP server, duckdb MCP server, excel MCP (excellm, live open workbooks), excel-mcp server (closed workbook COM automation), fetch MCP server, filesystem MCP server (scoped finance folder), github MCP server (+21 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (26): Initialize-AlfredEmbeddedLogo(), Enable-AlfredDoubleBuffer(), Get-AlfredBrandIcon(), Get-AlfredBrandImage(), Get-AlfredExePath(), Get-AlfredInstallerRoot(), Get-AlfredLogoBitmap(), Get-AlfredLogoSource() (+18 more)

### Community 32 - "Community 32"
Cohesion: 0.14
Nodes (30): analyzeVisualContrast(), analyzeVisualContrastCandidate(), checkColors(), checkElementAIPaletteDOM(), checkElementColors(), checkElementColorsDOM(), checkElementGlow(), checkElementGlowDOM() (+22 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (20): Add-PathEntry(), Add-ProcessPathEntry(), Find-Command(), Get-PythonExe(), Refresh-Path(), Install-Node-Portable(), Install-Python-NoAdmin(), Get-AlfredNpmToolList() (+12 more)

### Community 34 - "Community 34"
Cohesion: 0.16
Nodes (26): analyzeSourceHint(), buildCandidatesForOp(), buildContextHintsByRef(), buildManualEditEvidence(), collectSearchFiles(), countOps(), decodeBasicHtml(), escapeRegExp() (+18 more)

### Community 35 - "Community 35"
Cohesion: 0.10
Nodes (24): Alfred-specific rules, Core Rules (coding agent guidelines), Alfred-Common.ps1, Alfred-CoreSetup.ps1, andrej-karpathy-skills (multica-ai GitHub), backend/config/env.py, backend/context.py, backend/diagnostics/ (+16 more)

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (20): Complete-InstallStage(), Confirm-AlfredAuthLogin(), Get-AlfredInstallerRoot(), Get-InstallDefaultYes(), Import-AlfredInstallerModules(), Install-Tool(), Install-Uv(), Invoke-AlfredPowerShellScript() (+12 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (24): completionAckForAcceptResult(), completionTypeForAcceptResult(), augmentEventWithAcceptHandling(), buildAcceptScriptArgs(), buildPollReplyPayload(), EVENT_TYPES_NEEDING_AGENT_REPLY, fetchNextEvent(), fetchServerStatus() (+16 more)

### Community 38 - "Community 38"
Cohesion: 0.10
Nodes (21): Alfred-Doctor.ps1, Alfred-Reset.ps1, Installer overhaul (work profile, skills sync, per-project rules+graphify, doctor), backend/cli.py, backend/main.py (deprecated shim), cursor/mcp.json, fal-ai MCP, scripts/Fix-AzureKubeAuth.ps1 (+13 more)

### Community 39 - "Community 39"
Cohesion: 0.28
Nodes (23): _all_for_project(), _bar(), cmd_decay(), cmd_export(), cmd_import(), cmd_list(), cmd_prune(), cmd_record() (+15 more)

### Community 40 - "Community 40"
Cohesion: 0.19
Nodes (24): clearStoredManualApplyState(), fetchPendingCount(), handleManualEditActivity(), hidePendingApplyDock(), manualApplyLoadingText(), manualApplyStateKey(), manualEditEventForCurrentPage(), numberOrNull() (+16 more)

### Community 41 - "Community 41"
Cohesion: 0.10
Nodes (22): Claude Code hooks deep-dive (exit codes, HOOK_INPUT, UserPromptSubmit), Claude Code Plan Mode (Shift+Tab / --plan), CoALA framework (Cognitive Architecture for Language Agents, Princeton 2023), Iteration 10: Agent MCP Security Patterns, Iteration 11: Agent Output Evaluation — builder-validator pattern, Iteration 12: Claude Code native sub-agents (Task tool), Iteration 13: Agent Token Efficiency — effort levels + prompt caching, Iteration 14: Four-Layer Agent Memory System (CoALA framework) (+14 more)

### Community 42 - "Community 42"
Cohesion: 0.16
Nodes (20): buildMissingTargetDirective(), buildResolvedContextDirective(), buildTargetSelectionDirective(), buildUpdateDirective(), cli(), compareSemver(), computeUpdateDirective(), DESIGN_NAMES (+12 more)

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (21): bumpEditCount(), clampGroupedToBudget(), clampToBudget(), dedupeAgainstCache(), depthIsSet(), directiveFooter(), ensureFile(), ensureSession() (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (21): applyPlaceholderDimensions(), beginEditPin(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), clampPlaceholderSize(), finalizeEditingPin(), initAnnotOverlay() (+13 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (21): averageRgb01(), captureAndEmit(), captureChromeNodes(), captureElementFromRenderedAncestor(), captureElementToBlob(), compileShader(), cssColorToRgb01(), dominantRgb01() (+13 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (15): get_github_token(), get_tavily_api_key(), Environment variable and secret helpers., Read Tavily API key from env or .claude/settings.json., Find a GitHub PAT from .env or Claude MCP settings., capability_status(), load_mcp_servers(), MCP manifest loading and runtime status checks. (+7 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (18): Write or update a single KEY=value line in a .env file., write_env_var(), claude_auth_ready(), codex_auth_ready(), Executable resolution, auth checks, and repair helpers., repair_claude_login(), repair_codex_login(), repair_excel_mcp() (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.11
Nodes (20): checkElementHeroEyebrow(), checkElementHeroEyebrowDOM(), checkElementOversizedH1(), checkElementOversizedH1DOM(), checkElementQuality(), checkElementQualityDOM(), checkHeroEyebrow(), checkOversizedH1() (+12 more)

### Community 49 - "Community 49"
Cohesion: 0.14
Nodes (19): checkPageTypography(), checkTypography(), isBrandFontOnOwnDomain(), checkStaticPageTypography(), checkBorders(), checkElementBorders(), checkElementBordersDOM(), checkPageTypography() (+11 more)

### Community 50 - "Community 50"
Cohesion: 0.21
Nodes (17): isLiveServerPidReachable(), readLiveServerInfo(), completeCli(), completeThroughServer(), parseArgs(), readServerInfo(), collectManualApplyFiles(), manualApplyReplyCommand() (+9 more)

### Community 51 - "Community 51"
Cohesion: 0.11
Nodes (17): Alfred GitHub repo account (andrewcornell2000-Work/Alfred), Alfred Gmail account (alfredTCP2000@gmail.com), Alfred Supabase account (queryable brain, PENDING), ECC continuous-learning-v2 (ported engine source), ECC harness (affaan-m/ECC), scripts/instinct-cli.py, Instinct (confidence-scored when-X-do-Y lesson), supabase MCP server (+9 more)

### Community 52 - "Community 52"
Cohesion: 0.18
Nodes (18): Enable-AlfredHeadlessInstallLogging(), Initialize-AlfredInstallUi(), Show-InstallerConsole(), Show-InstallerFatalError(), Wait-InstallerExitPause(), Enable-AlfredGuiInstallOutput(), Hide-AlfredConsole(), Initialize-AlfredConsoleWindowType() (+10 more)

### Community 53 - "Community 53"
Cohesion: 0.23
Nodes (17): ArgumentParser, build_parser(), cmd_diagnose(), cmd_legacy_chat(), cmd_provision(), cmd_status(), cmd_update(), cmd_validate() (+9 more)

### Community 54 - "Community 54"
Cohesion: 0.19
Nodes (17): load_tool_manifest(), mcp_runtime_status(), _count_cursor_rules(), format_diagnose_report(), format_status_summary(), Plain-text diagnostic and status reporting., Short one-screen status for `alfred status`., Developer-focused health report for `alfred diagnose`. (+9 more)

### Community 55 - "Community 55"
Cohesion: 0.22
Nodes (18): resolveProjectRoot(), firstExisting(), getDesignSidecarCandidates(), getDesignSidecarPath(), getImpeccableDir(), getLegacyLiveAnnotationsDir(), getLegacyLiveConfigPath(), getLegacyLiveServerPath() (+10 more)

### Community 56 - "Community 56"
Cohesion: 0.25
Nodes (18): checkColors(), checkElementAIPaletteDOM(), checkElementColors(), checkElementColorsDOM(), checkElementGlow(), checkElementGlowDOM(), checkGlow(), parseColorResolved() (+10 more)

### Community 57 - "Community 57"
Cohesion: 0.24
Nodes (14): args, cwd, pageUrlFilter, remaining, summarizePendingManualEditBatch(), countByPage(), getBufferPath(), readBuffer() (+6 more)

### Community 58 - "Community 58"
Cohesion: 0.12
Nodes (16): Co-work protocol (design-agent alongside feature agents), graphify query orientation before design work, Jean Paul (design-agent persona), agents/design-agent.md (Jean Paul subagent def), Theme system (Alfred/themes/<id>/THEME.md), agents/janitor.md (Janitor subagent def), Janitor never-touch list (.git, node_modules, .venv, graphify-out), Janitor prime directives (sweep=delete to Recycle Bin, keep only essential, look before delete) (+8 more)

### Community 59 - "Community 59"
Cohesion: 0.17
Nodes (17): borderColorsFromStyle(), borderWidthsFromStyle(), checkElementGptBorderShadow(), checkElementGptBorderShadowDOM(), checkGptThinBorderWideShadow(), checkQuality(), colorsNearlyMatch(), cssColorAlpha() (+9 more)

### Community 60 - "Community 60"
Cohesion: 0.18
Nodes (16): blendRgba(), clampByte(), firstCssUrl(), getLayerValue(), loadVisualContrastImage(), parseObjectPosition(), parsePositionPair(), parsePositionToken() (+8 more)

### Community 61 - "Community 61"
Cohesion: 0.13
Nodes (16): browserColorsClose(), browserHasDirectText(), browserRadiusTokens(), browserSampleText(), buildSelectorSegment(), checkElementDesignSystemDOM(), generateSelector(), isBrowserDesignColorAllowed() (+8 more)

### Community 62 - "Community 62"
Cohesion: 0.20
Nodes (16): applyParamDefaults(), applyParamValue(), buildCyclingRow(), closedClipPath(), cycleVariant(), getVisibleVariantEl(), hideParamsPanel(), navBtn() (+8 more)

### Community 63 - "Community 63"
Cohesion: 0.14
Nodes (14): Diagnostic playbook (quarantine/audit trail read), Golden rule: DLP table reads FactPlan, not Bronze, agents/dlp-doctor.md (DLP Doctor subagent def), Alfred_Adidas_Weekly_Activity_Report_2026.xlsx, DF_Bronze_Plans dataflow, DF_Silver_Audit dataflow (Audit_UnknownTaskKeys), DF_Silver_Dimensions dataflow (DimActivityCodes), DF_Silver_FactPlan dataflow (FactPlan, FactPlan_Quarantine) (+6 more)

### Community 64 - "Community 64"
Cohesion: 0.16
Nodes (8): iter_control_tower_capabilities(), Unified capability registry for diagnostics and skill metadata., Register a new capability. Appears in diagnostics and skill metadata., Capability rows for `backend.cli diagnose`., register_tool(), Backward-compatible shim — canonical registry lives in provision.registry., Registry structure tests., RegistryTests

### Community 65 - "Community 65"
Cohesion: 0.16
Nodes (14): contextSourcePath(), contextSourceStatus(), firstExisting(), isCandidateProjectRoot(), isPathInside(), isPathInsideOrEqual(), nearestPackageRootBetween(), resolveCandidateContextSummary() (+6 more)

### Community 66 - "Community 66"
Cohesion: 0.25
Nodes (12): extractRegister(), cli(), COMMON_DEV_PORTS, devServerSignals(), gatherSignals(), gitSignals(), hasCode(), latestCritique() (+4 more)

### Community 67 - "Community 67"
Cohesion: 0.26
Nodes (13): loadContext(), resolveTargetSelection(), safeRead(), __dirname, ensureServerRunning(), globToRegex(), globToRegex(), resolveFiles() (+5 more)

### Community 68 - "Community 68"
Cohesion: 0.18
Nodes (14): browserDesignSystemConfig(), browserFindingsFromMap(), browserPrimaryFont(), checkBrowserDesignSystemSources(), checkCreamPalette(), checkHtmlPatterns(), checkPageQualityDOM(), checkPageQualityFromDoc() (+6 more)

### Community 70 - "Community 70"
Cohesion: 0.21
Nodes (13): directChildDirs(), discoverRootsForPattern(), discoverTargetCandidates(), expandSimplePattern(), findMonorepoRoot(), findTargetExample(), hasFallbackWorkspaceChildren(), hasGitBoundary() (+5 more)

### Community 71 - "Community 71"
Cohesion: 0.32
Nodes (11): kebab(), listSnapshotsForSlug(), main(), nowFilenameStamp(), parseFrontmatter(), readLatestSnapshot(), readTrend(), serializeFrontmatter() (+3 more)

### Community 72 - "Community 72"
Cohesion: 0.18
Nodes (13): addBrowserFindings(), addVisualContrastFindings(), addVisualContrastResult(), clearOverlays(), detachOverlay(), disconnectLazyVisualContrastObserver(), postExtensionError(), rememberVisualContrastAnalysis() (+5 more)

### Community 73 - "Community 73"
Cohesion: 0.17
Nodes (11): DLP Doctor hard rules (never edit Gen1 dataflow, clean temp tables), Device-code auth forbidden rule, alfred-tools.json, @anthropic-ai/claude-code CLI (claude), @openai/codex CLI (codex), DANGEROUS_KEYWORDS list (delete, remove, overwrite, credentials, password, ...), Forbidden auth rule (no device-code auth for agent actions), requirements/safety-gates.md (Safety gates doc) (+3 more)

### Community 74 - "Community 74"
Cohesion: 0.20
Nodes (4): Add-Failure(), Add-Warning(), Write-Fail(), Write-Warn2()

### Community 75 - "Community 75"
Cohesion: 0.23
Nodes (7): count_skills(), iter_skill_files(), Skill inventory helpers for diagnostics and validation., Yield (display_name, path) for skills/*.md and skills/_packs/**/SKILL.md., Return skill inventory counts and any unreadable files., Skill inventory tests., SkillLoaderTests

### Community 76 - "Community 76"
Cohesion: 0.23
Nodes (10): createLiveBrowserDomHelpers(), activeElementDeep(), appendStyleToLiveUiRoot(), appendToLiveUiRoot(), escapeCssIdent(), getLiveUiElementById(), LIVE_CHROME_MOUNT_CONTRACT, LIVE_UI_COMPONENT_IDS (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.27
Nodes (9): applyEvent(), baseSnapshot(), COMPLETED_PHASES, getJournalPath(), getSnapshotPath(), rebuildSnapshotFromJournal(), safeSessionId(), toPendingEvent() (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.24
Nodes (7): args, buildWeights(), hashUnit(), pickSeed(), seed, SEEDS, weightedPick()

### Community 79 - "Community 79"
Cohesion: 0.25
Nodes (9): __dirname, findHarnessDirs(), generatePinnedSkill(), HARNESS_DIRS, loadCommandMetadata(), pin(), root, unpin() (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.29
Nodes (10): escapeRegExp(), isExcludedByWorkspacePattern(), MONOREPO_FALLBACK_PROJECT_DIRS, nearestProjectLikeRoot(), normalizeWorkspacePattern(), projectRootFromDoubleStarPattern(), projectRootFromWorkspacePattern(), resolveWorkspaceProjectRoot() (+2 more)

### Community 81 - "Community 81"
Cohesion: 0.36
Nodes (10): cleanIgnoreValueDisplay(), extractFindingIgnoreValue(), extractFindingIgnoreValueRaw(), extractMotionIgnoreValue(), filterFindings(), formatFindingIgnoreCommand(), isIgnoredFindingValue(), normalizeIgnoreRule() (+2 more)

### Community 82 - "Community 82"
Cohesion: 0.27
Nodes (10): bindEditBadgeProxy(), editBadgeProxyTargets(), initEditBadge(), initEditBadgeHitProxies(), positionEditBadge(), proxyMouseEvent(), setImportantStyle(), styleEditBadgeProxy() (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.47
Nodes (8): _drain_stdin(), _extract(), _git_bits(), main(), Path, _read_transcript_tail(), _text_from_content(), _write_handoff()

### Community 84 - "Community 84"
Cohesion: 0.28
Nodes (9): checkElementTextOverflowDOM(), classSelector(), clippedByInset(), clippedByRect(), expandBoxShorthand(), firstMetricLengthPx(), isScreenReaderOnlyTextStyle(), metricLengthPx() (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.25
Nodes (8): Skill precedence (project-aware): project rules > theme > between-steps-ux > impeccable > ui-design-brain > frontend-design > accessibility > design-taste-frontend > Magic UI, Magic UI MCP, accessibility skill, between-steps-ux skill, design-taste-frontend skill, frontend-design skill, impeccable skill, ui-design-brain skill

### Community 86 - "Community 86"
Cohesion: 0.32
Nodes (7): Alfred-Install.exe, check-updates.ps1, What Alfred Is (2026-07): Windows installer/toolchain pack, Provision-Cursor.ps1, Install flow (git clone / Alfred-Install.exe), run-alfred.bat, setup.ps1

### Community 87 - "Community 87"
Cohesion: 0.46
Nodes (7): check_cursorrules(), check_discovered_tools(), check_mcp(), check_skills(), load_json(), main(), Path

### Community 89 - "Community 89"
Cohesion: 0.32
Nodes (8): parseYamlFlowList(), readJson(), readLernaWorkspaces(), readPackageWorkspaces(), readPnpmWorkspaces(), readWorkspacePatterns(), stripYamlInlineComment(), unquoteYamlValue()

### Community 90 - "Community 90"
Cohesion: 0.36
Nodes (8): coLocatedStylesheets(), expandScanTargets(), hasPathTraversal(), isInsideProject(), normalizeScanTargets(), parseStaticStyleImports(), STYLE_EXTS, UI_CODE_EXTS

### Community 91 - "Community 91"
Cohesion: 0.38
Nodes (5): _is_allowlisted(), _iter_text_files(), NoDeviceCodeAuthTests, Path, Acceptance: Alfred-owned docs must not normalize device-code auth.  Corporate

### Community 93 - "Community 93"
Cohesion: 0.43
Nodes (4): parseTargetOptions(), parseTargetPath(), TargetArgError, resolveLiveTarget()

### Community 94 - "Community 94"
Cohesion: 0.33
Nodes (6): assembleLiveBrowserScript(), assertLiveBrowserScriptParts(), LIVE_BROWSER_SCRIPT_PARTS, readLiveBrowserScriptParts(), resolveLiveBrowserScriptParts(), loadBrowserScripts()

### Community 95 - "Community 95"
Cohesion: 0.53
Nodes (4): Reset-JsonConfig(), Write-Info(), Write-OK(), Write-Warn2()

### Community 96 - "Community 96"
Cohesion: 0.60
Nodes (5): Get-AlfredLogoContentBounds(), Get-AlfredLogoMarkBounds(), New-AlfredGoldLayerBitmap(), Test-AlfredLogoGoldPixel(), Test-AlfredLogoNavyPixel()

### Community 98 - "Community 98"
Cohesion: 0.70
Nodes (4): hasGeneratedHeader(), HEADER_MARKERS, isGeneratedFile(), isGitIgnored()

### Community 100 - "Community 100"
Cohesion: 0.50
Nodes (3): main(), Backward-compatible entry point for Alfred.  The interactive chat/menu CLI was, Deprecated entry: runs ``backend.cli update`` (check updates + provision).

### Community 101 - "Community 101"
Cohesion: 0.50
Nodes (3): Shared Resend email helper for Alfred GitHub Actions workflows., Send a plain-text email to Andrew via Resend. Returns True if sent., send_alfred_email()

### Community 102 - "Community 102"
Cohesion: 0.83
Nodes (3): Get-AlfredAgentProcesses(), Stop-AlfredAgentProcesses(), Write-AgentCloseMsg()

### Community 104 - "Community 104"
Cohesion: 0.83
Nodes (3): main(), staged_content(), staged_files()

### Community 105 - "Community 105"
Cohesion: 0.67
Nodes (3): _load(), main(), Path

### Community 106 - "Community 106"
Cohesion: 0.50
Nodes (3): candidates, detectorPath, __dirname

### Community 107 - "Community 107"
Cohesion: 0.83
Nodes (3): captureVisualContrastCandidate(), compareScreenshotContrast(), sanitizeScreenshotClip()

### Community 108 - "Community 108"
Cohesion: 0.83
Nodes (3): writeAuditLog(), main(), readStdin()

## Knowledge Gaps
- **205 isolated node(s):** `${powerBiMcp}`, `${repoRoot}\.venv\Scripts\python.exe`, `${repoRoot}\bin\excel-mcp\mcp-excel.exe`, `docker`, `GITHUB_PERSONAL_ACCESS_TOKEN` (+200 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `el()` connect `Community 14` to `Community 32`, `Community 1`, `Community 2`, `Community 3`, `Community 68`, `Community 0`, `Community 6`, `Community 4`, `Community 8`, `Community 48`, `Community 49`, `Community 17`, `Community 29`, `Community 21`, `Community 61`, `Community 62`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `buffer` connect `Community 9` to `Community 2`, `Community 98`, `Community 108`, `Community 19`, `Community 20`, `Community 57`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `v()` connect `Community 7` to `Community 0`, `Community 66`, `Community 48`, `Community 17`, `Community 26`, `Community 29`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `el()` (e.g. with `browserFindingsFromMap()` and `collectVisualContrastCandidates()`) actually correct?**
  _`el()` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `initGlobalBar()` (e.g. with `hideAgentPollTooltip()` and `onDetectMessage()`) actually correct?**
  _`initGlobalBar()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `${powerBiMcp}`, `${repoRoot}\.venv\Scripts\python.exe`, `${repoRoot}\bin\excel-mcp\mcp-excel.exe` to the rest of the system?**
  _205 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.031492248062015504 - nodes in this community are weakly interconnected._