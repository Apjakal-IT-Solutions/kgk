# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Performance testing and optimization utilities
Profiles queries, measures response times, and identifies bottlenecks
"""

import frappe
from frappe.utils import cint, flt, now_datetime
import time
import json
from datetime import datetime, timedelta


class PerformanceProfiler:
    """Profile and measure system performance"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
    
    def start(self, operation_name):
        """Start timing an operation"""
        self.operation_name = operation_name
        self.start_time = time.time()
        self.query_count_start = len(frappe.db.sql_list("SELECT 1"))
    
    def end(self):
        """End timing and record results"""
        if not self.start_time:
            return
        
        duration = time.time() - self.start_time
        query_count_end = len(frappe.db.sql_list("SELECT 1"))
        query_count = query_count_end - self.query_count_start
        
        result = {
            "operation": self.operation_name,
            "duration_ms": duration * 1000,
            "query_count": query_count,
            "timestamp": now_datetime()
        }
        
        self.results.append(result)
        return result
    
    def report(self):
        """Generate performance report"""
        if not self.results:
            return "No performance data collected"
        
        report = "PERFORMANCE REPORT\n"
        report += "=" * 80 + "\n\n"
        
        for result in self.results:
            report += f"Operation: {result['operation']}\n"
            report += f"  Duration: {result['duration_ms']:.2f}ms\n"
            report += f"  Queries: {result['query_count']}\n"
            report += f"  Timestamp: {result['timestamp']}\n\n"
        
        # Summary statistics
        total_duration = sum(r['duration_ms'] for r in self.results)
        avg_duration = total_duration / len(self.results)
        
        report += "SUMMARY\n"
        report += "-" * 80 + "\n"
        report += f"Total Operations: {len(self.results)}\n"
        report += f"Total Duration: {total_duration:.2f}ms\n"
        report += f"Average Duration: {avg_duration:.2f}ms\n"
        
        return report


def profile_invoice_generation(iterations=100):
    """Profile invoice number generation performance"""
    print(f"Profiling invoice generation ({iterations} iterations)...")
    
    profiler = PerformanceProfiler()
    company = "_Test Company"
    test_date = frappe.utils.today()
    
    # Clean up
    frappe.db.delete("Cash Document", {
        "company": company,
        "transaction_date": test_date
    })
    frappe.db.commit()
    
    from kgk_customisations.tests.test_cash_document import create_test_cash_document
    
    for i in range(iterations):
        profiler.start(f"Invoice Generation {i+1}")
        
        doc = create_test_cash_document(
            company=company,
            transaction_date=test_date,
            main_document_type="Receipt",
            amount=1000
        )
        doc.insert()
        
        profiler.end()
        
        if (i + 1) % 10 == 0:
            frappe.db.commit()
    
    frappe.db.commit()
    
    print(profiler.report())
    return profiler.results


def profile_balance_calculation(days=30):
    """Profile daily balance calculation performance"""
    print(f"Profiling balance calculation ({days} days)...")
    
    profiler = PerformanceProfiler()
    company = "_Test Company"
    
    from kgk_customisations.kgk_customisations.doctype.daily_cash_balance.daily_cash_balance import calculate_erp_balance
    
    for day in range(days):
        test_date = frappe.utils.add_days(frappe.utils.today(), -day)
        
        profiler.start(f"Balance Calculation Day {day+1}")
        
        try:
            balance = calculate_erp_balance(test_date, company)
        except:
            balance = 0
        
        profiler.end()
    
    print(profiler.report())
    return profiler.results


def profile_report_generation():
    """Profile report generation performance"""
    print("Profiling report generation...")
    
    profiler = PerformanceProfiler()
    
    filters = {
        "from_date": frappe.utils.add_days(frappe.utils.today(), -30),
        "to_date": frappe.utils.today(),
        "company": "_Test Company"
    }
    
    # Test Daily Cash Summary
    profiler.start("Daily Cash Summary Report")
    from kgk_customisations.kgk_customisations.report.daily_cash_summary.daily_cash_summary import execute
    columns, data, message, chart = execute(filters)
    profiler.end()
    
    # Test Variance Analysis
    profiler.start("Variance Analysis Report")
    from kgk_customisations.kgk_customisations.report.variance_analysis.variance_analysis import execute
    columns, data, message, chart = execute(filters)
    profiler.end()
    
    # Test Cash Flow Analysis
    profiler.start("Cash Flow Analysis Report")
    from kgk_customisations.kgk_customisations.report.cash_flow_analysis.cash_flow_analysis import execute
    columns, data, message, chart = execute(filters)
    profiler.end()
    
    print(profiler.report())
    return profiler.results


def analyze_slow_queries():
    """Analyze and identify slow database queries"""
    print("Analyzing slow queries...")
    
    # Enable query logging
    frappe.db.sql("SET profiling = 1")
    
    # Run typical operations
    company = "_Test Company"
    test_date = frappe.utils.today()
    
    # Query 1: Get all documents for a date
    start = time.time()
    docs = frappe.get_all("Cash Document",
        filters={
            "company": company,
            "transaction_date": test_date
        },
        fields=["name", "amount", "main_document_type"]
    )
    query1_time = time.time() - start
    
    # Query 2: Get balance with variance
    start = time.time()
    balances = frappe.db.sql("""
        SELECT 
            balance_date, 
            company, 
            manual_balance, 
            erp_balance, 
            variance_percentage
        FROM `tabDaily Cash Balance`
        WHERE company = %s
        AND balance_date >= %s
        ORDER BY balance_date DESC
    """, (company, frappe.utils.add_days(test_date, -30)), as_dict=1)
    query2_time = time.time() - start
    
    # Query 3: Aggregate by document type
    start = time.time()
    aggregates = frappe.db.sql("""
        SELECT 
            main_document_type,
            COUNT(*) as count,
            SUM(amount) as total
        FROM `tabCash Document`
        WHERE company = %s
        AND transaction_date >= %s
        AND docstatus = 1
        GROUP BY main_document_type
    """, (company, frappe.utils.add_days(test_date, -30)), as_dict=1)
    query3_time = time.time() - start
    
    # Get profiling results
    profiles = frappe.db.sql("SHOW PROFILES", as_dict=1)
    
    print("\nSLOW QUERY ANALYSIS")
    print("=" * 80)
    print(f"Query 1 (Get Documents): {query1_time*1000:.2f}ms")
    print(f"Query 2 (Get Balances): {query2_time*1000:.2f}ms")
    print(f"Query 3 (Aggregates): {query3_time*1000:.2f}ms")
    print("\nRecent Query Profiles:")
    for profile in profiles[-10:]:
        print(f"  {profile.get('Duration', 0)*1000:.2f}ms - {profile.get('Query', '')[:60]}")
    
    frappe.db.sql("SET profiling = 0")


def suggest_optimizations():
    """Analyze schema and suggest optimizations"""
    print("\nPERFORMANCE OPTIMIZATION SUGGESTIONS")
    print("=" * 80)
    
    suggestions = []
    
    # Check for missing indexes
    tables = ["Cash Document", "Daily Cash Balance", "Cash Document Audit Trail"]
    
    for table in tables:
        indexes = frappe.db.sql(f"""
            SHOW INDEXES FROM `tab{table}`
        """, as_dict=1)
        
        # Check if commonly queried fields are indexed
        index_fields = {idx['Column_name'] for idx in indexes}
        
        if table == "Cash Document":
            required_indexes = ['company', 'transaction_date', 'invoice_number', 'main_document_type']
        elif table == "Daily Cash Balance":
            required_indexes = ['company', 'balance_date', 'status']
        else:
            required_indexes = ['document_type', 'document_name', 'timestamp']
        
        missing = set(required_indexes) - index_fields
        if missing:
            suggestions.append(f"Add indexes to {table}: {', '.join(missing)}")
    
    # Check table sizes
    for table in tables:
        count = frappe.db.count(table)
        if count > 10000:
            suggestions.append(f"Consider archiving old records in {table} (current: {count} records)")
    
    # Check for N+1 query patterns
    suggestions.append("Use batch queries instead of loops for fetching related documents")
    suggestions.append("Implement caching for frequently accessed company/user data")
    suggestions.append("Consider using Redis for session and cache storage")
    
    # Check query cache
    cache_status = frappe.db.sql("SHOW VARIABLES LIKE 'query_cache%'", as_dict=1)
    for var in cache_status:
        print(f"{var['Variable_name']}: {var['Value']}")
    
    if suggestions:
        print("\nSUGGESTIONS:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
    else:
        print("\nNo optimization suggestions at this time.")


def load_test_concurrent_operations(num_threads=10, operations_per_thread=20):
    """Simulate concurrent user operations"""
    import threading
    import queue
    
    print(f"\nLOAD TESTING: {num_threads} threads, {operations_per_thread} ops each")
    print("=" * 80)
    
    results_queue = queue.Queue()
    company = "_Test Company"
    test_date = frappe.utils.today()
    
    def worker():
        from kgk_customisations.tests.test_cash_document import create_test_cash_document
        
        for i in range(operations_per_thread):
            start = time.time()
            
            try:
                doc = create_test_cash_document(
                    company=company,
                    transaction_date=test_date,
                    main_document_type="Receipt",
                    amount=1000
                )
                doc.insert()
                frappe.db.commit()
                
                duration = time.time() - start
                results_queue.put(("success", duration))
            except Exception as e:
                duration = time.time() - start
                results_queue.put(("error", duration, str(e)))
    
    # Start threads
    threads = []
    start_time = time.time()
    
    for i in range(num_threads):
        thread = threading.Thread(target=worker)
        threads.append(thread)
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Analyze results
    successes = 0
    errors = 0
    durations = []
    
    while not results_queue.empty():
        result = results_queue.get()
        if result[0] == "success":
            successes += 1
            durations.append(result[1])
        else:
            errors += 1
            print(f"Error: {result[2]}")
    
    # Report
    print(f"\nTotal Time: {total_time:.2f}s")
    print(f"Successful Operations: {successes}")
    print(f"Failed Operations: {errors}")
    print(f"Operations/Second: {(successes + errors) / total_time:.2f}")
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        print(f"\nOperation Durations:")
        print(f"  Average: {avg_duration*1000:.2f}ms")
        print(f"  Min: {min_duration*1000:.2f}ms")
        print(f"  Max: {max_duration*1000:.2f}ms")


def generate_performance_report():
    """Generate comprehensive performance report"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE PERFORMANCE REPORT")
    print("=" * 80 + "\n")
    
    # 1. Invoice generation performance
    print("1. INVOICE GENERATION PERFORMANCE")
    print("-" * 80)
    profile_invoice_generation(iterations=50)
    
    # 2. Balance calculation performance
    print("\n2. BALANCE CALCULATION PERFORMANCE")
    print("-" * 80)
    profile_balance_calculation(days=7)
    
    # 3. Report generation performance
    print("\n3. REPORT GENERATION PERFORMANCE")
    print("-" * 80)
    profile_report_generation()
    
    # 4. Slow query analysis
    print("\n4. SLOW QUERY ANALYSIS")
    print("-" * 80)
    analyze_slow_queries()
    
    # 5. Optimization suggestions
    print("\n5. OPTIMIZATION SUGGESTIONS")
    print("-" * 80)
    suggest_optimizations()
    
    print("\n" + "=" * 80)
    print("Report generation complete")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "invoice":
            iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            profile_invoice_generation(iterations)
        
        elif command == "balance":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            profile_balance_calculation(days)
        
        elif command == "reports":
            profile_report_generation()
        
        elif command == "queries":
            analyze_slow_queries()
        
        elif command == "optimize":
            suggest_optimizations()
        
        elif command == "load_test":
            threads = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            load_test_concurrent_operations(num_threads=threads)
        
        elif command == "full":
            generate_performance_report()
        
        else:
            print("Unknown command")
    else:
        print("Usage: python performance_profiler.py <command>")
        print("Commands: invoice|balance|reports|queries|optimize|load_test|full")
