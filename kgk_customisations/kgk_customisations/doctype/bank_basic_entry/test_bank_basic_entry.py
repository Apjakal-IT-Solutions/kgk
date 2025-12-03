# Test Cases for Bank Basic Entry

1. **Entry Creation**
   - Create new bank entry
   - Validate date and balance requirements
   - Check auto-population of entered_by

2. **Verification Workflow**
   - Verify unverified entry
   - Check verified_by and verified_at population
   - Test unverify (System Manager only)

3. **Balance Calculations**
   - Test get_totals_by_date() with multiple entries
   - Test get_balance_by_user() for specific user
   - Verify set_bank_balance() creates/updates correctly

4. **Daily Balance Integration**
   - Test integrate_with_daily_balance()
   - Verify Daily Cash Balance updated with bank totals
   - Check multi-company handling
