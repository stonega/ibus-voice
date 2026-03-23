# AGENTS.md

This document defines how AI agents should work in this repository.

Agents must follow these conventions when reading, modifying, or generating code and documentation for `ibus-voice`.

---

# 1. Project Purpose

This repository is for a Linux project that adds voice input support to the IBus input framework.

The expected direction of the project is:

- integrate with IBus as an input method or companion service
- capture microphone audio on Linux
- send audio to a speech-to-text backend
- commit recognized text into the active application through IBus

Agents must keep work aligned with that purpose and avoid adding unrelated features.

---

# 2. Project Structure

Repository layout:

project/
├ README.md
├ LICENSE
├ AGENTS.md
├ docs/
│   ├ design/          # architecture and system design
│   ├ implementation/  # technical implementation notes
│   ├ research/        # experiments and investigations
│   ├ reference/       # API references and external resources
│   └ user/            # end-user documentation
│
├ src/                 # main source code
├ tests/               # automated tests
├ scripts/             # automation scripts
├ examples/            # usage examples
└ postmortem/          # incident reports and retrospectives

Agents should preserve this structure.

If a directory does not exist yet, agents may create it when needed, but should not invent parallel structures that overlap with the layout above.

---

# 3. Development Workflow

Agents must follow this workflow when implementing features:

1. Read relevant documents in:

   - `docs/design/`
   - `docs/implementation/`
   - `docs/research/` when evaluating backend or architecture choices

2. Implement code inside:

   - `src/`

3. Add or update tests inside:

   - `tests/`

4. Update documentation when behavior, architecture, setup, or workflows change.

5. Prefer incremental changes that keep the project runnable and understandable.

---

# 4. Coding Rules

Agents must follow these rules:

- Do not introduce new frameworks or large dependencies without clear justification
- Prefer small, composable modules over large files with mixed responsibilities
- Prefer readability over cleverness
- Avoid duplication
- Keep Linux and IBus integration concerns explicit instead of hiding them behind vague abstractions
- Favor practical implementations over speculative architecture

When modifying code:

- Prefer editing existing modules over creating new ones
- Follow existing naming conventions
- Keep public interfaces minimal
- Add comments only where behavior would otherwise be unclear

When making architectural choices:

- Prefer solutions that work well on Linux desktops
- Be explicit about whether speech recognition is local, remote, or pluggable
- Keep accessibility and latency in mind

---

# 5. Testing Requirements

All new features should include tests when practical.

Tests must be placed in:

- `tests/`

Test guidelines:

- Prefer unit tests for isolated logic
- Add integration tests for important workflows such as audio handling, backend adapters, or text commit behavior
- Tests must be deterministic
- Avoid tests that depend on external network services unless the repository explicitly supports that mode
- Mock speech backends, microphone input, and IBus interactions where appropriate

Agents should run relevant tests before finishing a task when test infrastructure exists.

If tests cannot be run, agents must state that clearly.

---

# 6. Documentation Rules

Documentation must be updated when:

- architecture changes
- setup or installation steps change
- APIs or interfaces change
- backend behavior changes
- new workflows are added

Docs location rules:

- Architecture: `docs/design/`
- Implementation detail: `docs/implementation/`
- Research notes: `docs/research/`
- Reference material: `docs/reference/`
- User documentation: `docs/user/`

The top-level `README.md` should stay concise and explain what the project is, why it exists, and how to get started.

---

# 7. Examples

When introducing new APIs, CLIs, or workflows, agents should add examples in:

- `examples/`

Examples should be runnable or close to runnable, and should reflect realistic Linux usage for this project.

---

# 8. Scripts

Automation scripts go into:

- `scripts/`

Examples include:

- build
- test
- lint
- local setup
- packaging
- development helpers

Scripts should be idempotent where practical and should avoid surprising system-wide changes.

---

# 9. Postmortems

When bugs, regressions, or operational failures occur, agents may create a report in:

- `postmortem/`

Suggested format:

- `incident.md`

Include:

- what happened
- root cause
- fix
- prevention

Agents should reference prior postmortems when they are relevant to avoid repeating mistakes.

---

# 10. Safety Rules

Agents must NOT:

- delete large sections of code without clear reason
- change the project structure without justification
- modify dependencies without explanation
- add cloud or remote-service assumptions unless clearly documented
- claim functionality exists when it has not been implemented

When unsure, agents should request clarification or make the smallest safe assumption.

---

# 11. Pull Request Expectations

Agent-generated changes should:

- follow the coding conventions in this file
- include tests when appropriate
- include documentation updates when required
- keep the repository focused on Linux voice input for IBus

Before finishing a task, agents should verify that:

- the change is internally consistent
- documentation matches the implementation
- any available relevant tests have been run or explicitly noted as not run
