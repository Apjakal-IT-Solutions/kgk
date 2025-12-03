# Test Cases for Cash Balance Submission

1. **Basic Submission Flow**
   - Create new submission
   - Submit basic balance
   - Verify status changes to "Basic Submitted"

2. **Checker Verification**
   - Verify checker can only submit after basic
   - Check variance calculation
   - Verify status changes to "Checker Verified"

3. **Accountant Finalization**
   - Verify accountant can only submit after checker
   - Check Daily Cash Balance update
   - Verify final variance alerts

4. **Rejection Workflow**
   - Test rejection at checker level
   - Test rejection at accountant level
   - Verify resubmission after rejection

5. **Variance Threshold**
   - Test with variance below threshold (no alert)
   - Test with variance above threshold (alert triggered)
   - Verify notification sent to Accounts Manager
