# Review checklist (Step 4)

Check each changed file for these items, in addition to Sections A–E. Put each hit in the Fix or the Report group with the Step 4 rules.

## Imports
- Unused, missing, or duplicate imports
- An import inside a function that belongs at module level (in non-test files)
- Import order: stdlib, third-party, local

## Code quality
- A variable that is not defined on every code path
- `raise e` instead of `raise`, which loses the traceback
- A bare `except:`
- An f-string in a logging call; use `extra={}` for structured logging
- A hard-coded value that should be a constant, or a magic number with no explanation
- A condition that is too complex or redundant, for example `x is not None and x != ""` where `x` is enough
- Deeply nested code that can be flat, or duplicated code that can be one function

## Error handling
- A variable used in an `except` block that may not be defined
- A swallowed exception (`except: pass`) or a handler that is too broad
- A log message with no error context

## Logic
- Off-by-one errors
- Race conditions in async code
- Missing `None` checks
- A wrong operator (`=` vs `==`, `and` vs `or`)

## Test files
- An import inside a test function that belongs at module level
- A test with no assertion, or one that does not test the changed code
- A hard-coded date that breaks in the future

## Helpers
- Extract a helper only at these repetition counts:

  | Code | Extract at |
  |---|---|
  | Production code | 2 or more |
  | Test code | 4 or more; fewer stay inline, so each test reads alone |

- Put a helper method at the **bottom** of its class, and a test helper function at the **top** of the test file, after the imports.
- Start every helper name with `_`, for example `_build_response` or `_make_mock_account`.
- If the diff adds the repeated code, extracting it is a fix (Step 3). If the copies exist before the diff, report it.
