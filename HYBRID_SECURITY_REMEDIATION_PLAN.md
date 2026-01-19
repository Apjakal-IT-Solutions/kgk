# Hybrid Security Remediation Plan
## AI-Assisted Implementation with Human Oversight

**Plan Date:** January 19, 2026  
**Approach:** AI Implementation + Human Review & Testing  
**Target Completion:** 3-4 weeks  
**Application:** kgk_customisations  

---

## Overview

This hybrid approach leverages AI for rapid code implementation while maintaining human oversight for critical decision-making, testing, and validation.

### Division of Responsibilities

| Task Type | AI Responsibility | Human Responsibility |
|-----------|------------------|---------------------|
| **Code Writing** | ✅ Implement fixes | ✅ Review code quality |
| **Testing** | ✅ Write unit tests | ✅ Manual security testing |
| **Security Review** | ✅ Scan & identify | ✅ Final approval |
| **Documentation** | ✅ Generate docs | ✅ Review accuracy |
| **Deployment** | ❌ Not applicable | ✅ Full ownership |
| **Architecture** | ✅ Propose solutions | ✅ Make final decisions |

---

## Week 1: Critical Vulnerabilities (AI-Driven Implementation)

### Day 1-2: SQL Injection Fixes

**AI Tasks (6 hours total):**
1. ✅ Create `utils/query_builder.py` with SafeQueryBuilder class
2. ✅ Refactor `stone_prediction_analysis.py`
3. ✅ Refactor `cash_flow_analysis.py`
4. ✅ Refactor `audit_trail_report.py`
5. ✅ Refactor all other report files with SQL queries
6. ✅ Write unit tests for SQL injection prevention
7. ✅ Generate documentation

**Human Tasks (4 hours total):**
- [ ] Review generated code for correctness
- [ ] Test queries return correct results
- [ ] Approve SafeQueryBuilder implementation
- [ ] Run manual SQL injection tests
- [ ] **Sign-off checkpoint**

**Deliverables:**
- Complete SafeQueryBuilder utility
- All reports refactored with parameterized queries
- Unit tests passing
- Documentation complete

---

### Day 3-4: Path Traversal Fixes

**AI Tasks (6 hours total):**
1. ✅ Create `utils/secure_file_access.py` with SecureFileAccess class
2. ✅ Refactor `utils/file_opener.py`
3. ✅ Refactor `file_management/Utils/file_operations.py`
4. ✅ Refactor `file_management/Utils/file_opener.py`
5. ✅ Update File Search Config to include allowed directories
6. ✅ Write unit tests for path traversal prevention
7. ✅ Generate documentation

**Human Tasks (4 hours total):**
- [ ] Define allowed directory list for your environment
- [ ] Review path validation logic
- [ ] Test file access with legitimate paths
- [ ] Attempt path traversal attacks manually
- [ ] **Sign-off checkpoint**

**Deliverables:**
- Complete SecureFileAccess utility
- All file operations secured
- Path validation working
- Unit tests passing

---

### Day 5: Permission Bypass - Quick Wins

**AI Tasks (4 hours):**
1. ✅ Audit all 48+ instances of `ignore_permissions=True`
2. ✅ Categorize by necessity (system vs user operations)
3. ✅ Generate permission check code for user operations
4. ✅ Implement permission checks in top 20 critical files
5. ✅ Create permission checking helper utilities
6. ✅ Write unit tests

**Human Tasks (3 hours):**
- [ ] Review categorization of permission bypasses
- [ ] Approve which bypasses can be removed
- [ ] Define role-to-permission mappings
- [ ] Test permission checks don't break workflows
- [ ] **Sign-off checkpoint**

**Deliverables:**
- 20+ critical permission checks implemented
- Categorization document
- Helper utilities created

---

### Week 1 Checkpoint: Critical Review Session

**Human-Led Session (2 hours):**
- [ ] Review all Week 1 changes
- [ ] Run security scans (Bandit)
- [ ] Manual penetration testing
- [ ] Decision: Proceed to Week 2 or iterate

**Exit Criteria:**
- ✅ All SQL injection tests pass
- ✅ All path traversal tests pass  
- ✅ Top 20 permission checks working
- ✅ No new bugs introduced
- ✅ Code review approved

---

## Week 2: High Severity Issues (AI-Driven)

### Day 1: File Upload Validation

**AI Tasks (4 hours):**
1. ✅ Create `utils/file_validator.py` with FileValidator class
2. ✅ Implement MIME type checking
3. ✅ Implement zip bomb detection
4. ✅ Refactor `doctype/ocr_data_upload/ocr_data_upload.py`
5. ✅ Refactor `doctype/parcel/parcel.py`
6. ✅ Refactor `doctype/parcel_import/parcel_import.py`
7. ✅ Write unit tests with malicious files
8. ✅ Generate documentation

**Human Tasks (2 hours):**
- [ ] Define allowed file types for your use cases
- [ ] Set appropriate file size limits
- [ ] Test with actual business files
- [ ] Attempt malicious file uploads
- [ ] **Sign-off checkpoint**

---

### Day 2: Access Control on Whitelisted Methods (Batch 1)

**AI Tasks (5 hours):**
1. ✅ Add access controls to 25 highest-risk methods:
   - Bulk operations (cash_document.py)
   - Financial operations (daily_cash_balance.py)
   - Import functions (bulk_import.py)
   - OCR operations (ocr_parcel_merge.py)
2. ✅ Create role checking decorators
3. ✅ Write permission tests

**Human Tasks (2 hours):**
- [ ] Review role assignments
- [ ] Test each protected method
- [ ] Verify error messages are user-friendly
- [ ] **Sign-off checkpoint**

---

### Day 3: Access Control on Whitelisted Methods (Batch 2)

**AI Tasks (5 hours):**
1. ✅ Add access controls to remaining 54 methods:
   - File operations
   - Report exports
   - Search functions
   - Configuration updates
2. ✅ Update documentation with required roles

**Human Tasks (2 hours):**
- [ ] Review remaining access controls
- [ ] Test workflows aren't broken
- [ ] Update user role assignments if needed

---

### Day 4: Logging Security

**AI Tasks (3 hours):**
1. ✅ Create `utils/secure_logging.py` with SecureLogger class
2. ✅ Implement data sanitization patterns
3. ✅ Replace all sensitive logging (50+ locations)
4. ✅ Remove all debug print() statements
5. ✅ Remove all console.log() in JavaScript
6. ✅ Generate logging policy document

**Human Tasks (2 hours):**
- [ ] Review sanitization patterns
- [ ] Verify legitimate debugging isn't impacted
- [ ] Test log output format
- [ ] **Sign-off checkpoint**

---

### Day 5: Remaining High Severity

**AI Tasks (4 hours):**
1. ✅ Move hardcoded paths to configuration
2. ✅ Implement basic rate limiting hooks
3. ✅ Add security headers to file downloads
4. ✅ Secure subprocess calls with validation
5. ✅ Verify CSRF protection configuration

**Human Tasks (2 hours):**
- [ ] Configure rate limits for your environment
- [ ] Test download security
- [ ] Review subprocess usage

---

### Week 2 Checkpoint: High Severity Review

**Human-Led Session (2 hours):**
- [ ] Review all Week 2 changes
- [ ] Integration testing
- [ ] Security scan
- [ ] Performance testing
- [ ] Decision: Proceed or iterate

**Exit Criteria:**
- ✅ All file uploads validated
- ✅ All 79 whitelisted methods have access controls
- ✅ Logging sanitized
- ✅ No sensitive data exposed
- ✅ Performance acceptable

---

## Week 3: Medium Severity & Testing

### Day 1-2: Medium Severity Fixes

**AI Tasks (8 hours):**
1. ✅ Strengthen input validation in data_validator.py
2. ✅ Improve error handling (specific exceptions)
3. ✅ Enhance audit logging for security events
4. ✅ Implement filename sanitization
5. ✅ Add length validation on inputs
6. ✅ Improve session security
7. ✅ Write comprehensive tests

**Human Tasks (4 hours):**
- [ ] Review validation rules
- [ ] Test error scenarios
- [ ] Verify audit logs complete
- [ ] **Sign-off checkpoint**

---

### Day 3-5: Comprehensive Testing

**AI Tasks (10 hours):**
1. ✅ Write comprehensive unit test suite
2. ✅ Create integration test scenarios
3. ✅ Generate security test cases
4. ✅ Create automated test scripts
5. ✅ Generate test report templates

**Human Tasks (12 hours):**
- [ ] Run all automated tests
- [ ] Manual security testing:
  - [ ] SQL injection attempts
  - [ ] Path traversal attempts
  - [ ] Permission bypass attempts
  - [ ] File upload exploits
  - [ ] XSS attempts
- [ ] Run security scanners:
  - [ ] Bandit
  - [ ] SonarQube
  - [ ] OWASP ZAP
  - [ ] SQLMap
- [ ] Performance testing
- [ ] User acceptance testing
- [ ] **Major checkpoint**

**Exit Criteria:**
- ✅ All automated tests pass
- ✅ Security scans clean
- ✅ Manual penetration tests pass
- ✅ No regressions found
- ✅ Performance acceptable

---

## Week 4: Documentation, Review & Deployment

### Day 1-2: Documentation

**AI Tasks (6 hours):**
1. ✅ Generate complete security architecture document
2. ✅ Create developer security guidelines
3. ✅ Write administrator setup guide
4. ✅ Create user security awareness guide
5. ✅ Generate detailed change log
6. ✅ Create migration guide
7. ✅ Update all inline code documentation

**Human Tasks (4 hours):**
- [ ] Review all documentation for accuracy
- [ ] Add environment-specific details
- [ ] Create custom diagrams if needed
- [ ] Translate/localize if needed

---

### Day 3: Final Review & Staging Deployment

**Human-Led Activities (8 hours):**
- [ ] Final code review session
- [ ] Stakeholder presentation
- [ ] Deploy to staging environment
- [ ] Smoke testing in staging
- [ ] Performance monitoring
- [ ] Security monitoring
- [ ] Get stakeholder sign-off

---

### Day 4-5: Production Deployment

**Collaborative Activities:**

**AI Support:**
- ✅ Generate deployment scripts
- ✅ Create rollback procedures
- ✅ Monitor for errors in logs
- ✅ Provide quick fixes if issues found

**Human Tasks (8 hours):**
- [ ] Backup production
- [ ] Deploy to production
- [ ] Monitor deployment
- [ ] Verify security controls active
- [ ] User communication
- [ ] Post-deployment testing
- [ ] Performance monitoring
- [ ] Create post-deployment report

---

## Workflow for Each Fix

### Standard Process

1. **AI Implementation** (1-2 hours per fix)
   - Write code following security best practices
   - Create unit tests
   - Generate documentation
   - Run automated checks
   - Present to human for review

2. **Human Review** (30-60 minutes per fix)
   - Review code logic
   - Check for edge cases
   - Verify tests are comprehensive
   - Approve or request changes

3. **Iteration if Needed**
   - AI makes requested changes
   - Human re-reviews
   - Repeat until approved

4. **Integration**
   - AI integrates approved fix
   - Runs full test suite
   - Human validates integration

---

## Communication Protocol

### Daily Sync (15 minutes)
**What AI reports:**
- Code completed since last sync
- Tests written and passing
- Issues encountered
- Next tasks planned

**What Human provides:**
- Feedback on previous work
- Approvals or change requests
- Priority adjustments
- Environment-specific details

### Weekly Review (1 hour)
- Comprehensive progress review
- Security scan results
- Integration testing results
- Next week planning
- Risk assessment

---

## Quality Gates

### Every Fix Must Pass:
1. ✅ AI self-review with security checklist
2. ✅ Automated tests passing
3. ✅ Security scanner clean (Bandit)
4. ✅ Human code review approval
5. ✅ Integration tests passing
6. ✅ Documentation complete

### Phase Gates (End of Each Week):
1. ✅ All fixes for phase complete
2. ✅ All tests passing
3. ✅ Manual security testing passed
4. ✅ No regressions detected
5. ✅ Stakeholder approval
6. ✅ Ready to proceed to next phase

---

## Risk Management

### AI Implementation Risks

| Risk | Mitigation |
|------|-----------|
| AI misunderstands requirement | Human reviews all code before integration |
| AI introduces new bugs | Comprehensive testing at each step |
| AI makes breaking changes | Test suites catch regressions |
| Code doesn't fit environment | Human provides environment details upfront |

### Human Review Risks

| Risk | Mitigation |
|------|-----------|
| Review bottleneck | Schedule dedicated review time |
| Miss subtle issues | Use checklist, multiple reviewers |
| Approval delays | Set SLA for reviews (24-48 hours) |

---

## Success Metrics

### Speed Metrics
- **AI Implementation Speed:** 4-6x faster than human-only
- **Total Timeline:** 3-4 weeks vs 10 weeks
- **Effort Reduction:** 60-70% reduction in developer hours

### Quality Metrics
- **Code Coverage:** >80% for security-related code
- **Security Scan:** 0 high/critical issues
- **Bug Introduction:** <5% regression rate
- **Review Quality:** 100% code review coverage

---

## Immediate Next Steps

### To Start This Week:

**Your Actions (30 minutes):**
1. Review and approve this hybrid plan
2. Provide environment-specific details:
   - Allowed file directories
   - File size limits
   - Role definitions
   - Rate limiting preferences
3. Schedule daily 15-minute syncs
4. Assign review responsibility

**AI Will Begin:**
1. Create SafeQueryBuilder utility
2. Fix first SQL injection vulnerability
3. Write tests
4. Present for your review

**First Deliverable (Day 1):**
- SafeQueryBuilder complete with tests
- First report file refactored
- Ready for your review

---

## How to Interact with AI During Implementation

### When Reviewing Code:

**Good Feedback:**
✅ "This query doesn't handle NULL values correctly"  
✅ "Add validation for negative numbers"  
✅ "Use company-specific allowed directories instead"  
✅ "This breaks the existing workflow for X users"

**AI Will Respond With:**
- Updated code addressing your concern
- Explanation of the fix
- Additional tests if needed

### When Requesting Changes:

**Examples:**
- "Make the error message more user-friendly"
- "Add logging for this security event"
- "Extract this into a separate function"
- "Add a configuration option for this threshold"

### When Approving:

Simply indicate:
- ✅ "Approved, proceed to next fix"
- ✅ "Looks good, integrate this"
- ✅ "LGTM (Looks Good To Me)"

---

## Tools & Access Needed

### For Human Reviewer:
- [ ] Access to development environment
- [ ] Ability to run tests locally
- [ ] Security scanning tools installed
- [ ] Code review permissions
- [ ] Staging environment access

### For AI:
- [ ] File system access (current workspace)
- [ ] Ability to read/write code files
- [ ] Access to run tests
- [ ] Access to documentation

---

## Emergency Procedures

### If Critical Issue Found

**Immediate Stop:**
1. AI stops current work
2. Focus on critical issue
3. Generate emergency fix
4. Human reviews immediately
5. Deploy hot-fix if approved
6. Return to regular schedule

### If Timeline Slips

**Week 1 Extension:**
- Reduce Week 3 scope (medium issues)
- Add 3-5 days to timeline

**Week 2 Extension:**
- Defer some medium issues to post-deployment
- Focus on critical/high only

---

## Post-Deployment Support

### AI Continues to Support:

**Week 5-6: Monitoring Period**
- Monitor error logs daily
- Identify any issues
- Generate fixes quickly
- Update documentation

**Ongoing:**
- Answer questions about implementations
- Suggest optimizations
- Help with new features
- Maintain security standards

---

## Cost-Benefit Analysis

### Traditional Approach (10 weeks):
- **Developer Time:** 240-310 hours
- **Cost:** $24,000 - $31,000 (at $100/hour)
- **Timeline:** 10 weeks
- **Risk:** Developer availability, knowledge gaps

### Hybrid Approach (3-4 weeks):
- **Developer Time:** 60-80 hours (review/testing)
- **AI Time:** 40-50 hours (implementation)
- **Cost:** $6,000 - $8,000 (developer time only)
- **Timeline:** 3-4 weeks
- **Benefit:** 
  - 70% cost reduction
  - 60% time reduction
  - Higher consistency
  - Better documentation

---

## Decision Points

### Go/No-Go Checkpoints:

**End of Week 1:**
- Are critical vulnerabilities fixed?
- Are tests passing?
- Any major issues found?
- **Decision:** Continue or extend Week 1

**End of Week 2:**
- Are high severity issues resolved?
- Any breaking changes?
- Performance acceptable?
- **Decision:** Continue or iterate

**End of Week 3:**
- All tests passing?
- Security scans clean?
- Ready for staging?
- **Decision:** Deploy to staging or extend testing

**End of Week 4:**
- Staging stable?
- Stakeholders approve?
- Production ready?
- **Decision:** Deploy to production

---

## Ready to Begin?

### When You Approve This Plan, AI Will:

**Immediately:**
1. Create `utils/query_builder.py`
2. Begin refactoring first report file
3. Write initial tests
4. Present first deliverable for review (~2 hours)

**First Review Session:**
- You review the SafeQueryBuilder code
- Test the refactored report
- Provide feedback
- Approve or request changes

**Then AI Continues:**
- Incorporate your feedback
- Move to next report file
- Maintain velocity
- Present each batch for review

---

**Your approval needed to begin. Ready when you are!** 🚀

---

## Appendix: Environment Details Template

Please provide the following for optimal AI implementation:

```yaml
# Environment Configuration

## File Access
allowed_directories:
  - /opt/bench/frappe-bench/sites/[SITE]/public/files
  - /opt/bench/frappe-bench/sites/[SITE]/private/files
  - [Add other directories]

## File Upload Limits
max_file_sizes:
  excel: 50  # MB
  pdf: 20    # MB
  image: 10  # MB
  video: 100 # MB

allowed_file_types:
  excel: ['.xlsx', '.xls', '.xlsb']
  pdf: ['.pdf']
  # Add others

## Roles & Permissions
roles:
  - name: Cash Super User
    permissions: [all]
  - name: Cash Manager
    permissions: [read, write, approve]
  # Add others

## Rate Limiting
rate_limits:
  api_calls: 100  # per minute
  file_uploads: 10  # per hour
  bulk_operations: 5  # per hour

## Deployment
site_url: https://your-site.com
staging_url: https://staging.your-site.com
```

Fill this out and AI can customize all implementations to your exact environment!
