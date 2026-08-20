# Codex Current Task

Status: **HOLD — no active implementation task**

Repository: `Fisker1111/Punkto`
Branch: `pilot-1`

## Purpose

This file is the canonical handoff from ChatGPT/product review to the local Codex implementation agent.

When this file says `HOLD`, Codex must not edit, commit, or push product code.

When a task is active, ChatGPT will replace this file with a scoped implementation contract containing:

- exact goal
- expected base branch / SHA
- allowed scope and files
- explicit exclusions
- acceptance criteria
- required automated checks
- required manual checks where practical
- expected commit message
- stop condition

## Current instruction

Do not make code changes.

If invoked now:

1. Confirm the repository is on `pilot-1` and up to date with `origin/pilot-1`.
2. Read `AGENTS.md`.
3. Report that there is no active implementation task.
4. Stop without modifying the working tree, committing, pushing, deploying, or starting Slice 3.

## Permanent handoff rule

Codex implements only the task written in this file and the repository-level rules in `AGENTS.md`.

After implementation, Codex must:

1. run the required checks against the exact working tree that will be committed;
2. commit only the scoped changes;
3. push the commit to the requested branch;
4. report the exact commit SHA;
5. stop.

Deployment is not Codex's job. AZ deploys only a SHA explicitly approved after GitHub CI and ChatGPT review.
