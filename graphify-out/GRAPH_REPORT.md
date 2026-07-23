# Graph Report - D:\Project\Utility-Maintenance-Disk  (2026-07-24)

## Corpus Check
- Corpus is ~14,631 words - fits in a single context window. You may not need a graph.

## Summary
- 230 nodes · 348 edges · 34 communities (11 shown, 23 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 19 edges (avg confidence: 0.8)
- Token cost: 53,000 input · 3,867 output

## Community Hubs (Navigation)
- Platform Backends (disktools)
- disktools Commands
- disktools Core Helpers
- Bash Shared Library
- Command Catalog & Win Mapping
- Bash Cleaner Suite
- Windows Port Architecture
- disk-inspect (bash) Internals
- disk-health (bash) Internals
- disktools Entry Point
- bloat-scan (bash) Internals
- Read-only Scanners & Philosophy
- install.sh Internals
- Cross-OS Safety Principles
- APT Cleaner
- Chrome AI Cleaner
- Chrome Cache Cleaner
- Service Worker Cleaner
- Docker Cleaner
- Journald Cleaner
- Junk Report Scanner
- Node Cache Cleaner
- Snap Cleaner
- System-Clean Orchestrator
- Trash Cleaner
- Self-Update Command
- Chrome AI (concept)
- disk-inspect (concept)
- Confirm-Before-Delete Principle
- Global Flags
- junk-report (concept)
- Status Color Thresholds
- update-cleaner (concept)

## God Nodes (most connected - your core abstractions)
1. `Drive` - 21 edges
2. `disk_inspect()` - 16 edges
3. `system_clean()` - 14 edges
4. `clean()` - 13 edges
5. `human()` - 12 edges
6. `main()` - 11 edges
7. `dir_size()` - 11 edges
8. `disk_health()` - 10 edges
9. `trash_clean()` - 10 edges
10. `Area` - 10 edges

## Surprising Connections (you probably didn't know these)
- `cross-OS safety principles` --semantically_similar_to--> `no age-based auto-delete principle`  [INFERRED] [semantically similar]
  docs/windows-plan.md → README.md
- `Windows-specific cleaners (Temp/WinUpdate cache/WinSxS/Windows.old/thumbcache)` --references--> `temp-clean command`  [INFERRED]
  docs/windows-plan.md → README.md
- `Linux-to-Windows concept/command mapping` --references--> `node-clean command`  [EXTRACTED]
  docs/windows-plan.md → README.md
- `Linux-to-Windows concept/command mapping` --references--> `chrome-clean command`  [EXTRACTED]
  docs/windows-plan.md → README.md
- `Linux-to-Windows concept/command mapping` --references--> `chrome-sw-clean command`  [EXTRACTED]
  docs/windows-plan.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Safe cleaners run in sequence by system-clean** — claude_system_clean, claude_chrome_clean, claude_chrome_sw_clean, claude_node_clean, claude_trash_clean, claude_journal_clean, claude_apt_clean, claude_docker_clean, claude_snap_clean [INFERRED 0.85]
- **system-clean safe-cleaner orchestration flow** — readme_system_clean, readme_temp_clean, readme_node_clean, readme_chrome_clean, readme_trash_clean [EXTRACTED 1.00]
- **Windows port architecture (Opsi A / Python)** — docs_windows_plan_option_a, docs_windows_plan_disktools_pkg, docs_windows_plan_os_detection, docs_windows_plan_concept_mapping [EXTRACTED 1.00]
- **safe-cleaner safety philosophy** — readme_confirm_principle, readme_no_age_delete, readme_safe_delete_marker, docs_windows_plan_cross_os_principles [INFERRED 0.85]

## Communities (34 total, 23 thin omitted)

### Community 0 - "Platform Backends (disktools)"
Cohesion: 0.08
Nodes (41): Area, dir_size(), A named bucket of paths (cache/junk/bloat) a backend measures or reclaims., Free `paths` by clearing their contents. Returns (measured_before, freed).     U, Sweep `roots` for model/weight files >= threshold. Read-only. Skips     symlinks, Sum of regular-file sizes under `path`. Skips reparse points (junctions/     sym, reclaim(), walk_big_files() (+33 more)

### Community 1 - "disktools Commands"
Cohesion: 0.17
Nodes (30): bloat_scan(), clean(), disk_health(), disk_inspect(), _gather(), _parse_delete_spec(), _print_areas(), Commands (OS-agnostic presentation). Each command takes the active platform back (+22 more)

### Community 2 - "disktools Core Helpers"
Cohesion: 0.11
Nodes (20): _delete_children(), delete_item(), Drive, err(), is_cache_junk(), is_sensitive(), list_children(), _on_rm_error() (+12 more)

### Community 4 - "Command Catalog & Win Mapping"
Cohesion: 0.12
Nodes (20): GenAI local-model anti-download registry policy, Linux-to-Windows concept/command mapping, Windows silent-bloat locations (AI models/Electron/dev caches), Windows-specific cleaners (Temp/WinUpdate cache/WinSxS/Windows.old/thumbcache), apt-clean command, bloat-scan command, chrome-ai-clean command, chrome-clean command (+12 more)

### Community 5 - "Bash Cleaner Suite"
Cohesion: 0.13
Nodes (16): apt-clean, chrome-clean, chrome-sw-clean, disk-health, docker-clean, install.sh, journal-clean, _lib.sh (shared helper library) (+8 more)

### Community 6 - "Windows Port Architecture"
Cohesion: 0.20
Nodes (9): disktools/ package architecture (__main__/core/commands/platform_*), Opsi A: Python unified cross-OS rewrite (chosen), Opsi B: native twin (bash + PowerShell) with shared spec, OS detection strategy, PowerShell 5.1 $IsWindows pitfall correction, disktools/ (Python Windows/Linux stack), install.ps1 (Windows installer), install.sh (Linux installer) (+1 more)

### Community 7 - "disk-inspect (bash) Internals"
Cohesion: 0.48
Nodes (5): disk-inspect script, inspect_path(), navigate(), safe_to_delete(), tree_view()

### Community 8 - "disk-health (bash) Internals"
Cohesion: 0.47
Nodes (4): disk-health script, CACHE_PATHS, line(), rec()

### Community 9 - "disktools Entry Point"
Cohesion: 0.40
Nodes (3): disktools — cross-platform disk-maintenance suite (Opsi A: Python unified).  One, _load_backend(), Entry point: detect OS -> load matching backend -> dispatch command.      python

### Community 11 - "Read-only Scanners & Philosophy"
Cohesion: 0.67
Nodes (3): bloat-scan, junk-report, 'Sampah lama' philosophy (no age-based auto-delete)

## Knowledge Gaps
- **29 isolated node(s):** `_lib.sh script`, `disk-inspect`, `bloat-scan`, `chrome-sw-clean`, `chrome-ai-clean` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Drive` connect `disktools Core Helpers` to `Platform Backends (disktools)`, `disktools Commands`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `dir_size()` connect `Platform Backends (disktools)` to `disktools Core Helpers`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `disk_inspect()` connect `disktools Commands` to `disktools Core Helpers`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **What connects `_lib.sh script`, `disk-inspect`, `bloat-scan` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Platform Backends (disktools)` be split into smaller, more focused modules?**
  _Cohesion score 0.07716701902748414 - nodes in this community are weakly interconnected._
- **Should `disktools Core Helpers` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._
- **Should `Bash Shared Library` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._