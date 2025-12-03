# KGK Customisations - Testing Guide

## Overview
Comprehensive testing suite for the Cash Management System migration from Django to Frappe.

## Test Structure

### 1. Unit Tests (`tests/`)
- **test_cash_document.py** - Cash Document functionality
- **test_daily_cash_balance.py** - Balance calculations and verification
- **test_integration.py** - Integration and workflow tests

### 2. Performance Testing
- **performance_profiler.py** - Performance profiling utilities
- **query_optimizer.py** - Query optimization and caching

### 3. Data Integrity
- **data_integrity_validator.py** - Database integrity checks

### 4. Security Testing
- **security_auditor.py** - Security vulnerability scanning

### 5. User Acceptance Testing
- **uat_scenarios.py** - End-to-end user workflows

### 6. Test Data
- **test_data_generator.py** - Generate realistic test data

## Running Tests

### Quick Start
```bash
# Navigate to app directory
cd /opt/bench/frappe-bench/apps/kgk_customisations

# Run all unit tests
bench --site kgkerp.local run-tests --app kgk_customisations

# Run specific test module
python -m kgk_customisations.tests.test_cash_document

# Run all tests with coverage
python -m kgk_customisations.tests
```

### Detailed Test Commands

#### Unit Tests
```bash
# Run Cash Document tests
python -m kgk_customisations.tests.test_cash_document

# Run Daily Balance tests
python -m kgk_customisations.tests.test_daily_cash_balance

# Run integration tests
python -m kgk_customisations.tests.test_integration
```

#### Performance Testing
```bash
# Profile invoice generation (100 iterations)
bench execute kgk_customisations.tests.performance_profiler.profile_invoice_generation --kwargs "{'iterations': 100}"

# Profile balance calculation (30 days)
bench execute kgk_customisations.tests.performance_profiler.profile_balance_calculation --kwargs "{'days': 30}"

# Profile report generation
bench execute kgk_customisations.tests.performance_profiler.profile_report_generation

# Analyze slow queries
bench execute kgk_customisations.tests.performance_profiler.analyze_slow_queries

# Run load test (10 threads)
bench execute kgk_customisations.tests.performance_profiler.load_test_concurrent_operations --kwargs "{'num_threads': 10}"

# Full performance report
bench execute kgk_customisations.tests.performance_profiler.generate_performance_report
```

#### Query Optimization
```bash
# Create recommended indexes
bench execute kgk_customisations.tests.query_optimizer.QueryOptimizer.create_missing_indexes

# Clear all caches
bench execute kgk_customisations.tests.query_optimizer.CacheManager.clear_all_caches
```

#### Data Integrity Validation
```bash
# Run all integrity checks
bench execute kgk_customisations.tests.data_integrity_validator.DataIntegrityValidator.validate_all

# Fix balance mismatches
bench execute kgk_customisations.tests.data_integrity_validator.fix_balance_mismatches
```

#### Security Audit
```bash
# Run full security audit
bench execute kgk_customisations.tests.security_auditor.SecurityAuditor.run_full_audit

# Audit permission configuration
bench execute kgk_customisations.tests.security_auditor.test_permission_roles
```

#### User Acceptance Testing
```bash
# Run all UAT scenarios
bench execute kgk_customisations.tests.uat_scenarios.run_all_uat_scenarios
```

#### Test Data Generation
```bash
# Generate 30 days of test data
bench execute kgk_customisations.tests.test_data_generator.generate_test_data --kwargs "{'days': 30}"

# Create edge case scenarios
bench execute kgk_customisations.tests.test_data_generator.create_edge_case_data

# Create workflow test data
bench execute kgk_customisations.tests.test_data_generator.create_workflow_test_data

# Create performance test data (1000 documents)
bench execute kgk_customisations.tests.test_data_generator.create_performance_test_data --kwargs "{'num_documents': 1000}"

# Cleanup all test data
bench execute kgk_customisations.tests.test_data_generator.cleanup_test_data
```

## Test Coverage Areas

### Core Functionality (✅ Covered)
- Invoice number generation (atomic, sequential, unique)
- Company name auto-population
- Year field auto-population
- File suffix assignment
- Balance calculations
- Workflow state transitions
- Amount validation
- Document type validation
- Audit trail creation

### Integration Testing (✅ Covered)
- End-to-end receipt workflow
- Balance reconciliation
- Document cancellation
- Multi-company operations
- Scheduled task execution
- Report generation

### Performance Testing (✅ Covered)
- Invoice generation performance
- Balance calculation performance
- Report generation performance
- Slow query analysis
- Concurrent operation handling
- Load testing

### Data Integrity (✅ Covered)
- Invoice uniqueness
- Balance accuracy
- Workflow consistency
- Foreign key validation
- Amount consistency
- Date logic validation
- Audit trail completeness

### Security (✅ Covered)
- SQL injection prevention
- XSS attack prevention
- Permission enforcement
- API authentication
- Data sanitization
- Audit trail integrity

### UAT Scenarios (✅ Covered)
- Daily receipt processing
- Three-tier balance verification
- Month-end reconciliation
- Workflow approval process

## Best Practices

### Before Testing
1. Create test company: `_Test Company`
2. Backup production database
3. Use dedicated test site if possible

### During Testing
1. Run unit tests before integration tests
2. Use test data generator for realistic scenarios
3. Monitor performance metrics
4. Document any failures

### After Testing
1. Review all test results
2. Fix any identified issues
3. Run integrity validation
4. Clean up test data

## Continuous Integration

### Pre-Commit Checks
```bash
# Run quick tests
python -m kgk_customisations.tests.test_cash_document

# Check data integrity
bench execute kgk_customisations.tests.data_integrity_validator.DataIntegrityValidator.validate_all
```

### Pre-Deployment Checks
```bash
# Full test suite
python -m kgk_customisations.tests

# Security audit
bench execute kgk_customisations.tests.security_auditor.SecurityAuditor.run_full_audit

# Performance baseline
bench execute kgk_customisations.tests.performance_profiler.generate_performance_report

# UAT scenarios
bench execute kgk_customisations.tests.uat_scenarios.run_all_uat_scenarios
```

## Troubleshooting

### Common Issues

**Issue: Tests fail with permission errors**
```bash
# Run as Administrator
bench --site kgkerp.local set-admin-password <password>
```

**Issue: Database connection errors**
```bash
# Restart MariaDB
sudo systemctl restart mariadb
```

**Issue: Import errors**
```bash
# Reinstall app
bench --site kgkerp.local uninstall-app kgk_customisations
bench --site kgkerp.local install-app kgk_customisations
```

**Issue: Test data conflicts**
```bash
# Clean up test data
bench execute kgk_customisations.tests.test_data_generator.cleanup_test_data
```

## Performance Benchmarks

### Target Metrics
- Invoice generation: < 50ms per document
- Balance calculation: < 100ms per day
- Report generation: < 2s for 30 days
- Concurrent operations: > 50 ops/second

### Optimization Checklist
- [ ] Database indexes created
- [ ] Query caching enabled
- [ ] Batch operations implemented
- [ ] N+1 queries eliminated
- [ ] Redis configured for caching

## Test Maintenance

### Monthly Tasks
- Review and update test data
- Update performance baselines
- Review security audit findings
- Update UAT scenarios

### Quarterly Tasks
- Full regression testing
- Load testing with production-like data
- Security penetration testing
- Documentation updates

## Support

For issues or questions:
1. Check test output for error messages
2. Review test logs in `logs/` directory
3. Consult this guide for common solutions
4. Contact development team

---

**Last Updated:** December 2025
**Version:** 1.0
