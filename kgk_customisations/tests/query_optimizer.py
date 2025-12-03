# Copyright (c) 2025, KGK and contributors
# For license information, please see license.txt

"""
Query optimization utilities and caching strategies
Provides optimized queries and caching helpers
"""

import frappe
from frappe.utils import cint, flt, get_datetime
import hashlib
import json


class QueryOptimizer:
    """Optimize database queries for better performance"""
    
    @staticmethod
    def get_documents_batch(filters, limit=1000, offset=0):
        """Get documents in batches to avoid memory issues"""
        return frappe.db.sql("""
            SELECT 
                name, company, transaction_date, main_document_type, 
                amount, invoice_number, workflow_state
            FROM `tabCash Document`
            WHERE company = %(company)s
            AND transaction_date >= %(from_date)s
            AND transaction_date <= %(to_date)s
            AND docstatus = 1
            ORDER BY transaction_date DESC, creation DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """, {
            "company": filters.get("company"),
            "from_date": filters.get("from_date"),
            "to_date": filters.get("to_date"),
            "limit": limit,
            "offset": offset
        }, as_dict=1)
    
    @staticmethod
    def get_balances_optimized(company, from_date, to_date):
        """Optimized query for balance retrieval"""
        return frappe.db.sql("""
            SELECT 
                balance_date,
                company,
                manual_balance,
                erp_balance,
                variance_amount,
                variance_percentage,
                status,
                verified_by
            FROM `tabDaily Cash Balance`
            WHERE company = %(company)s
            AND balance_date BETWEEN %(from_date)s AND %(to_date)s
            ORDER BY balance_date ASC
        """, {
            "company": company,
            "from_date": from_date,
            "to_date": to_date
        }, as_dict=1)
    
    @staticmethod
    def get_aggregates_by_type(company, from_date, to_date):
        """Optimized aggregation query"""
        return frappe.db.sql("""
            SELECT 
                main_document_type,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(transaction_date) as first_date,
                MAX(transaction_date) as last_date
            FROM `tabCash Document`
            WHERE company = %(company)s
            AND transaction_date BETWEEN %(from_date)s AND %(to_date)s
            AND docstatus = 1
            GROUP BY main_document_type
        """, {
            "company": company,
            "from_date": from_date,
            "to_date": to_date
        }, as_dict=1)
    
    @staticmethod
    def create_missing_indexes():
        """Create recommended indexes for performance"""
        indexes = [
            # Cash Document indexes
            ("Cash Document", "company_date_idx", ["company", "transaction_date"]),
            ("Cash Document", "invoice_number_idx", ["invoice_number"]),
            ("Cash Document", "workflow_state_idx", ["workflow_state"]),
            ("Cash Document", "doc_type_idx", ["main_document_type"]),
            
            # Daily Cash Balance indexes
            ("Daily Cash Balance", "company_date_idx", ["company", "balance_date"]),
            ("Daily Cash Balance", "status_idx", ["status"]),
            
            # Audit Trail indexes
            ("Cash Document Audit Trail", "doc_ref_idx", ["document_type", "document_name"]),
            ("Cash Document Audit Trail", "timestamp_idx", ["timestamp"]),
            ("Cash Document Audit Trail", "activity_idx", ["activity_type"])
        ]
        
        for table, index_name, columns in indexes:
            try:
                # Check if index exists
                existing = frappe.db.sql(f"""
                    SHOW INDEX FROM `tab{table}` 
                    WHERE Key_name = '{index_name}'
                """)
                
                if not existing:
                    column_list = ", ".join(columns)
                    frappe.db.sql(f"""
                        CREATE INDEX {index_name} 
                        ON `tab{table}` ({column_list})
                    """)
                    print(f"✓ Created index {index_name} on {table}")
                else:
                    print(f"⊘ Index {index_name} already exists on {table}")
            except Exception as e:
                print(f"✗ Error creating index {index_name}: {str(e)}")


class CacheManager:
    """Manage caching for frequently accessed data"""
    
    CACHE_PREFIX = "kgk_cash:"
    DEFAULT_TTL = 300  # 5 minutes
    
    @staticmethod
    def _get_cache_key(key_parts):
        """Generate cache key from parts"""
        key_string = json.dumps(key_parts, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{CacheManager.CACHE_PREFIX}{key_hash}"
    
    @classmethod
    def get_cached_balance(cls, company, balance_date):
        """Get cached daily balance"""
        cache_key = cls._get_cache_key(["balance", company, str(balance_date)])
        
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch from database
        balance = frappe.db.get_value("Daily Cash Balance",
            {
                "company": company,
                "balance_date": balance_date
            },
            ["manual_balance", "erp_balance", "variance_amount", "status"],
            as_dict=1
        )
        
        if balance:
            frappe.cache().set_value(cache_key, json.dumps(balance), expires_in_sec=cls.DEFAULT_TTL)
        
        return balance
    
    @classmethod
    def get_cached_company_data(cls, company):
        """Get cached company information"""
        cache_key = cls._get_cache_key(["company", company])
        
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return json.loads(cached)
        
        # Fetch from database
        company_data = frappe.db.get_value("Company",
            company,
            ["company_name", "abbr", "default_currency"],
            as_dict=1
        )
        
        if company_data:
            # Cache for longer (company data doesn't change often)
            frappe.cache().set_value(cache_key, json.dumps(company_data), expires_in_sec=3600)
        
        return company_data
    
    @classmethod
    def invalidate_balance_cache(cls, company, balance_date):
        """Invalidate balance cache when data changes"""
        cache_key = cls._get_cache_key(["balance", company, str(balance_date)])
        frappe.cache().delete_value(cache_key)
    
    @classmethod
    def clear_all_caches(cls):
        """Clear all KGK caches"""
        # Get all cache keys with our prefix
        keys = frappe.cache().get_value("cache_keys") or []
        for key in keys:
            if key.startswith(cls.CACHE_PREFIX):
                frappe.cache().delete_value(key)
        
        print("✓ All KGK caches cleared")


def optimize_report_query(report_name, filters):
    """Optimize report queries with caching and batching"""
    cache_key = CacheManager._get_cache_key([report_name, filters])
    
    # Check cache
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return json.loads(cached)
    
    # Execute report
    if report_name == "Daily Cash Summary":
        from kgk_customisations.kgk_customisations.report.daily_cash_summary.daily_cash_summary import execute
    elif report_name == "Variance Analysis":
        from kgk_customisations.kgk_customisations.report.variance_analysis.variance_analysis import execute
    else:
        return None
    
    columns, data, message, chart = execute(filters)
    
    # Cache result
    result = {
        "columns": columns,
        "data": data,
        "chart": chart
    }
    frappe.cache().set_value(cache_key, json.dumps(result), expires_in_sec=180)
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create_indexes":
            QueryOptimizer.create_missing_indexes()
        
        elif command == "clear_cache":
            CacheManager.clear_all_caches()
        
        else:
            print("Unknown command. Use: create_indexes|clear_cache")
    else:
        print("Usage: python query_optimizer.py <command>")
