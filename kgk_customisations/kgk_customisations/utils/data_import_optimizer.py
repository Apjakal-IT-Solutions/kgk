"""
Optimize Data Import for Invoice Processing - Handle Large Datasets
"""

import frappe
from frappe.desk.form.save import SaveDocument

# Store original save handler
_original_save_docs = SaveDocument.save_documents

def optimized_save_documents(self, docs):
    """
    Optimized save handler for bulk imports.
    Routes large data imports to background jobs.
    """
    try:
        # Check if this is a data import operation
        if hasattr(self, 'doc') and self.doc.get('doctype') == 'Data Import':
            data_import = self.doc
            
            # Check if this is Invoice Processing import with significant data
            if (data_import.get('reference_doctype') == 'Invoice Processing' and 
                data_import.get('import_file')):
                
                # Get file size to determine if we should process in background
                try:
                    import os
                    file_path = frappe.get_site_path(data_import.get('import_file'))
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        # If file is larger than 5MB, queue as background job
                        if file_size > 5 * 1024 * 1024:
                            frappe.enqueue(
                                'frappe.core.doctype.data_import.data_import.DataImport.start_import',
                                name=data_import.get('name'),
                                queue='long',
                                timeout=1200
                            )
                            frappe.msgprint(
                                'Large data import queued for background processing. You will be notified when complete.',
                                title='Import Queued'
                            )
                            # Mark as queued
                            frappe.db.set_value('Data Import', data_import.get('name'), 'status', 'Queued')
                            return {'docs': docs}
                except Exception as e:
                    frappe.logger().warning(f"Could not queue large import: {str(e)}")
                    # Fall through to regular processing
    
    except Exception as e:
        frappe.logger().error(f"Error in optimized save: {str(e)}")
        # Fall through to original method
    
    # Use original method
    return _original_save_docs(self, docs)

# Apply the optimization
try:
    SaveDocument.save_documents = optimized_save_documents
    frappe.logger().info("[kgk_customisations] Applied data import optimization for large datasets")
except Exception as e:
    frappe.logger().warning(f"[kgk_customisations] Could not apply save optimization: {str(e)}")
