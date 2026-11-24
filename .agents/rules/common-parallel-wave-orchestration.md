---
trigger: model_decision
description: "Protocol for dispatching parallel subagents in waves with disjoint file and resource ownership, preventing file collisions and commit races."
---
# Parallel Subagent-Driven Development (Wave Orchestration)

## Ownership Rules

- **File collisions** are prevented by only forming a parallel wave from tasks whose file sets are fully disjoint. If two tasks might touch the same file, they never run in the same wave.
- **Commit races** are prevented by removing self-committing from subagents entirely. Subagents leave their changes in the working tree; the coordinator validates and commits after the wave finishes.
- **Resource collisions** require independent mutable resources for each task (ports, build directories, test databases, or services), or serialization of the affected work.

## Task Tagging

At plan time, every delegated task gets three fields:

- **`Files:`** — exact file paths or globs the task will create or modify.
- **`Resources:`** — ports, build directories, test databases, and services used by the task or its checks, with their isolation or `none`.
- **`Depends-on:`** — IDs of tasks whose output this task consumes, or `none`.

If any field is uncertain, treat the task as depending on everything before it (fail-safe serial execution).

## Wave Formation Rule

Two tasks belong in the same wave only if **all** hold:

1. Neither task is in the other's `Depends-on` chain, even transitively.
2. Their `Files` sets are fully disjoint.
3. Their mutable resources are independent or explicitly isolated.

## Per-Wave Execution Loop

1. Write one task brief per task with files, dependencies, resources, acceptance criteria, and checks.
2. Dispatch every implementer or reviewer in the wave in a single turn.
3. Workers do **not** run `git commit`. Each worker reports which files it touched or reviewed.
4. The coordinator verifies integration, runs checks that share resources serially, and records one consolidated update per wave.
