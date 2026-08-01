## Workspace Instructions

### Context updates after aib-modify

These directives apply to every successful execution of `.aib_brain/prompts/aib-modify.md`.

- MUST: After implementation completes successfully, and before archiving `input.md`, moving request artifacts, or closing the request, re-read `.aib_memory/context.md` and `.aib_brain/conventions/context-convention.md`.

- MUST: Determine and apply the `context.md` changes resulting from the implementation. Base these changes only on request items actually implemented and decisions actually applied. Do not record skipped, deferred, failed, or unimplemented request items.

- MUST: Record durable, high-level product descriptions, concepts, requirements, architectural decisions, implementation approaches, and unresolved product-relevant issues when they provide useful context that is not readily available elsewhere.

- MUST NOT: Record low-level or readily derivable implementation details such as source-code behavior, function signatures, command-line arguments, comments, tests, configuration values, or similar details.

- MUST NOT: Duplicate facts that are already explicitly recorded and easily discoverable in other workspace files.

- MUST: Modify `.aib_memory/context.md` only by executing `.aib_brain/tools/edit-context.py`. Do not directly edit, patch, rewrite, or replace `context.md`.

- CLARIFICATION: The prohibition in `aib-modify.md` against updating `context.md` prohibits direct modification of the file. It does not prohibit updates made through `edit-context.py`; the invocations required by these instructions are explicitly permitted.

- MUST: Execute the required `edit-context.py` invocations. Do not merely print or propose them.

- MUST: Use concrete, literal `--operation`, `--area`, `--text`, and `--workspace .` arguments for every inserted or deleted statement in the `Product`, `Concepts`, `Requirements`, `Solution`, and `Issues` areas.

- MUST: Include `--type MUST`, `--type "MUST NOT"`, or `--type OPTIONAL` only for inserts into `Requirements`. Do not include `--type` for deletions or for inserts into any other area.

- MUST: Represent a changed statement as a deletion of the existing statement followed by insertion of its replacement. For deletion, pass the complete existing statement text accepted by `edit-context.py`, not a shortened substring, to avoid ambiguous matches.

- MUST NOT: Use `--planned` for inserts. `aib-modify` records only current state established by the completed implementation.

- MUST: When the implementation realizes an existing `[PLANNED]` statement, delete the complete planned statement and insert its untagged current-state replacement. Preserve unrelated `[PLANNED]` statements unchanged.

- MUST: Insert into `Issues` only unresolved, product-relevant problems discovered during implementation. Do not record temporary implementation difficulties or problems resolved during the same execution. Delete existing Issues statements that the implementation resolved or made inapplicable.

- MUST: If any `edit-context.py` invocation exits with a non-zero status, halt immediately, report the tool error, and do not archive `input.md`, move request artifacts, or close the request.

- MUST: After all required `edit-context.py` invocations succeed, run `python .aib_brain/tools/verify-context.py --workspace .`. If verification fails, halt, report the validation errors, and do not archive `input.md`, move request artifacts, or close the request.

- MUST: After successful context verification, explicitly report every context statement inserted or deleted, identifying its operation and area. Do not report the commands themselves.

- MUST: If no context changes are necessary, execute no `edit-context.py` invocations and report `Context updates: none.


- MUST: Place the context-update report before the final completion line required by `aib-modify.md`.

### Maintain user report

- MUST: Maintain a file `workdir/chronicles.md` where after each modify or implement prompt adds in several bullets explanation for non-technical audience what was changed.

- MUST: Group the entries for each modify or implement prompt under `##` header with the request name

- MUST: Make additions to `workdir/chronicles.md` at the bottom of the file

- MUST: Use Bulgarian language

- MUST: Create the file `workdir/chronicles.md` if not exists.

- MUST NOT: Change the previous content of the file `workdir/chronicles.md` if exists.