# Consolidate tests

Use these rules when the user asks to consolidate, and at the end of an `--auto` run. Change only test files that this run touched. After the changes, run the tests of each changed file again.

## 1. Remove parameters that do not matter

For each call to a helper or factory in a test:
- Remove a parameter that has the same value as the default.
- Remove a parameter whose value the test never asserts and does not need, and use the default.

Before:
```python
async def test_validator_returns_failure_on_trade_mismatch(mocker):
    mock.return_value = _make_aggregation(
        total_quantity=Decimal("100"),
        pending_non_credit_quantity=Decimal("20"),  # default is fine
        pending_credit_quantity=Decimal("10"),       # default is fine
    )
    snapshot = _make_snapshot(
        trade=Decimal("999"),
        settled=Decimal("80"),             # not relevant to this test
        pending_withdrawal=Decimal("10"),  # not relevant to this test
    )
```

After:
```python
async def test_validator_returns_failure_on_trade_mismatch(mocker):
    mock.return_value = _make_aggregation(total_quantity=Decimal("100"))
    snapshot = _make_snapshot(trade=Decimal("999"))
```

## 2. Remove unused code

- Remove a variable that is assigned and never read.
- Remove a mock that is never asserted and that the code does not need to run.
- Move each import inside a test function to the top of the file.

## 3. Extract repeated setup

If the same mock patches, object construction, or assertion pattern repeats in 4 or more tests, extract it into a helper or a fixture. With fewer, keep it inline, so each test reads alone:
- Prefix a helper with `_`, for example `_make_mock_account`, and put it after the imports, before the tests.
- Put a long mock path in a module constant, for example `MODULE_PATH = "acme.payments.snapshots"`, then `mocker.patch(f"{MODULE_PATH}.store_snapshot")`.

Extract only if the tests become easier to read. Do not extract if the helper hides a detail that the test is about, needs many parameters, or makes the test harder to understand.

## 4. Simplify assertions

- If a list must hold exactly one item, assert `len()` first, then use the item by index, instead of filtering.
- Remove redundant assertions, for example `len(x) == 1` together with `x != []`.
