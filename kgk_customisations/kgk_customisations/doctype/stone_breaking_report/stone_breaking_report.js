// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function formatNumber(value) {
    return (value || 0).toFixed(2);
}

function formatPercent(value) {
    return `${formatNumber(value)}%`;
}

function updateElement(wrapper, selector, value) {
    const element = wrapper.find(selector);
    if (element.length) {
        element.text(value);
    } else {
        console.warn(`Element not found: ${selector}`);
    }
}

function recalculate_breaking_amount(frm) {
    let totalBreakingAmount = 0;
    if (frm.doc.article_workers) {
        frm.doc.article_workers.forEach(worker => {
            totalBreakingAmount += flt(worker.breaking_amount) || 0;
        });
    }
    frm.set_value('breaking_amount', totalBreakingAmount);
    frm.refresh_field('breaking_amount');
}

// ============================================================================
// SUMMARY DISPLAY FUNCTIONS
// ============================================================================

function updateWorkerTable(wrapper, workers) {
    const hasWorkers = workers && Object.keys(workers).length > 0;
    
    const html = hasWorkers
        ? Object.values(workers).map(worker => `
            <tr class="worker-data-row" style="border-bottom: 1px solid #ebeff2;">
                <td style="padding: 10px; color: #444;">${worker.employee_code || 'N/A'}</td>
                <td style="padding: 10px; color: #444;">${formatNumber(worker.breaking_amount)}</td>
                <td style="padding: 10px; color: #444;">${formatNumber(worker.org_plan_value)}</td>
                <td style="padding: 10px; color: #444;">${formatNumber(worker.breaking_percentage)}%</td>
            </tr>
        `).join('')
        : `<tr class="worker-data-row">
            <td colspan="4" style="padding: 10px; text-align: center; color: #999;">No worker data available</td>
        </tr>`;
    
    // Replace placeholder or existing worker rows
    const placeholder = wrapper.find('#worker_table_placeholder');
    const existingRows = wrapper.find('.worker-data-row');
    
    if (placeholder.length) {
        placeholder.replaceWith(html);
    } else if (existingRows.length) {
        existingRows.remove();
        wrapper.find('tbody').append(html);
    }
}

function updateSummarySection(wrapper, data, prefix) {
    const { stoneFault, workerFault } = data;
    
    // Breaking amounts
    updateElement(wrapper, `#${prefix}stone_amnt`, formatNumber(stoneFault.breaking_amount));
    updateElement(wrapper, `#${prefix}worker_amnt`, formatNumber(workerFault.breaking_amount));
    updateElement(wrapper, `#${prefix}total_amnt`, formatNumber(stoneFault.breaking_amount + workerFault.breaking_amount));
    
    // Org plan values
    updateElement(wrapper, `#${prefix}stone_org`, formatNumber(stoneFault.org_plan_value));
    updateElement(wrapper, `#${prefix}worker_org`, formatNumber(workerFault.org_plan_value));
    updateElement(wrapper, `#${prefix}total_org`, formatNumber(stoneFault.org_plan_value + workerFault.org_plan_value));
    
    // Percentages
    updateElement(wrapper, `#${prefix}stone_percent`, formatPercent(stoneFault.breaking_percentage));
    updateElement(wrapper, `#${prefix}worker_percent`, formatPercent(workerFault.breaking_percentage));
    updateElement(wrapper, `#${prefix}total_percent`, formatPercent(stoneFault.breaking_percentage + workerFault.breaking_percentage));
}

function display_breaking_summary(frm) {
    const wrapper = frm.fields_dict.breaking_report.$wrapper;
    const summary = frm.breaking_summary_totals;
    
    if (!summary) {
        console.warn('No breaking summary data available');
        return;
    }
    
    // Update worker table
    updateWorkerTable(wrapper, summary.workers);
    
    // Update month summary
    updateSummarySection(wrapper, summary.currentMonth, '');
    
    // Update YTD summary
    updateSummarySection(wrapper, summary.currentYear, 'ytd_');
}

// ============================================================================
// CURRENT DOCUMENT INCLUSION
// ============================================================================

function includeCurrentDocument(frm, currentMonthStoneFault, currentMonthWorkerFault, currentYearStoneFault, currentYearWorkerFault, workerStats, monthStartDate, fyStartDate) {
    // Only include if document has required data
    if (!frm.doc.breaking_amount || !frm.doc.org_plan_value) {
        console.log('Current document has no breaking data to include');
        return;
    }
    
    const breakingAmount = flt(frm.doc.breaking_amount) || 0;
    const orgPlanValue = flt(frm.doc.org_plan_value) || 0;
    const today = frappe.datetime.get_today();
    
    // Current document is always "current month" and check if it's in current FY
    const isCurrentFY = today >= fyStartDate;
    
    console.log('=== Including Current Document ===');
    console.log('Breaking Amount:', breakingAmount);
    console.log('Org Plan Value:', orgPlanValue);
    console.log('Stone Fault:', frm.doc.stone_fault);
    console.log('Worker Fault:', frm.doc.worker_fault);
    
    // Add to month summaries
    if (frm.doc.stone_fault) {
        currentMonthStoneFault.breaking_amount += breakingAmount;
        currentMonthStoneFault.org_plan_value += orgPlanValue;
        currentMonthStoneFault.count++;
        console.log('Added current doc to Month Stone Fault');
    } else if (frm.doc.worker_fault) {
        currentMonthWorkerFault.breaking_amount += breakingAmount;
        currentMonthWorkerFault.org_plan_value += orgPlanValue;
        currentMonthWorkerFault.count++;
        console.log('Added current doc to Month Worker Fault');
    } else {
        // Default to worker fault if neither is checked
        currentMonthWorkerFault.breaking_amount += breakingAmount;
        currentMonthWorkerFault.org_plan_value += orgPlanValue;
        currentMonthWorkerFault.count++;
        console.log('Added current doc to Month Worker Fault (default)');
    }
    
    // Add to year summaries
    if (isCurrentFY) {
        if (frm.doc.stone_fault) {
            currentYearStoneFault.breaking_amount += breakingAmount;
            currentYearStoneFault.org_plan_value += orgPlanValue;
            currentYearStoneFault.count++;
        } else if (frm.doc.worker_fault) {
            currentYearWorkerFault.breaking_amount += breakingAmount;
            currentYearWorkerFault.org_plan_value += orgPlanValue;
            currentYearWorkerFault.count++;
        } else {
            currentYearWorkerFault.breaking_amount += breakingAmount;
            currentYearWorkerFault.org_plan_value += orgPlanValue;
            currentYearWorkerFault.count++;
        }
    }
    
    // Add current document's workers to worker stats
    if (frm.doc.article_workers && frm.doc.article_workers.length > 0) {
        frm.doc.article_workers.forEach(worker => {
            const workerCode = worker.employee_code;
            if (workerStats[workerCode]) {
                workerStats[workerCode].breaking_amount += flt(worker.breaking_amount) || 0;
                workerStats[workerCode].org_plan_value += orgPlanValue;
                workerStats[workerCode].count++;
                console.log(`Added current doc to worker ${workerCode}:`, workerStats[workerCode]);
            }
        });
    }
}

// ============================================================================
// SUMMARY CALCULATION FUNCTION
// ============================================================================

function calculate_breaking_summary(frm) {
    if (!frm.doc.department) {
        console.log("Department not set, skipping summary calculation");
        return;
    }

    // Get current date info
    const today = frappe.datetime.get_today();
    const currentMonth = frappe.datetime.str_to_obj(today).getMonth() + 1;
    const currentYear = frappe.datetime.str_to_obj(today).getFullYear();
    
    // Calculate financial year (assuming April start)
    const fyStartMonth = 4; // April
    const fyStartYear = currentMonth >= fyStartMonth ? currentYear : currentYear - 1;
    const fyStartDate = `${fyStartYear}-${String(fyStartMonth).padStart(2, '0')}-01`;
    
    // Get current month start date
    const monthStartDate = `${currentYear}-${String(currentMonth).padStart(2, '0')}-01`;
    
    console.log('=== DEBUG: Date Ranges ===');
    console.log('Month Start:', monthStartDate);
    console.log('FY Start:', fyStartDate);
    console.log('Current Department:', frm.doc.department);
    
    // Fetch all Stone Breaking Report records
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Stone Breaking Report",
            fields: [
                "name", 
                "breaking_amount", 
                "org_plan_value", 
                "breaking_percent",
                "stone_fault",
                "worker_fault",
                "department",
                "creation"
            ],
            filters: [],
            limit_page_length: 0
        },
        callback: function(response) {
            if (!response.message) {
                console.log('No records found');
                return;
            }
            
            let records = response.message;
            
            // Filter out the current document if it exists in the fetched records
            // This prevents double-counting if the document is already saved
            if (frm.doc.name) {
                records = records.filter(rec => rec.name !== frm.doc.name);
                console.log('Filtered out current document from records');
            }
            
            console.log('=== DEBUG: Total Records Found (excluding current) ===', records.length);
            
            // Log first few records for debugging
            records.slice(0, 3).forEach((rec, idx) => {
                console.log(`Record ${idx + 1}:`, {
                    name: rec.name,
                    department: rec.department,
                    creation: rec.creation,
                    stone_fault: rec.stone_fault,
                    worker_fault: rec.worker_fault,
                    breaking_amount: rec.breaking_amount
                });
            });
            
            // Initialize summary objects
            const summaryStructure = {
                breaking_amount: 0,
                org_plan_value: 0,
                breaking_percentage: 0,
                count: 0
            };
            
            const currentMonthStoneFault = {...summaryStructure};
            const currentMonthWorkerFault = {...summaryStructure};
            const currentYearStoneFault = {...summaryStructure};
            const currentYearWorkerFault = {...summaryStructure};
            const workerStats = {};
            
            // Get worker names from current document
            const currentWorkers = frm.doc.article_workers 
                ? frm.doc.article_workers.map(w => w.employee_code)
                : [];
            
            console.log('=== DEBUG: Current Workers ===', currentWorkers);
            
            // Initialize worker stats
            currentWorkers.forEach(workerName => {
                workerStats[workerName] = {
                    employee_code: workerName,
                    breaking_amount: 0,
                    org_plan_value: 0,
                    breaking_percentage: 0,
                    count: 0
                };
            });
            
            // Counter for async operations
            let processedRecords = 0;
            const totalRecordsToProcess = records.length;
            
            // If no records, still display with current document data
            if (totalRecordsToProcess === 0) {
                finalizeSummaryCalculations(
                    frm,
                    currentMonthStoneFault,
                    currentMonthWorkerFault,
                    currentYearStoneFault,
                    currentYearWorkerFault,
                    workerStats,
                    monthStartDate,
                    fyStartDate
                );
                return;
            }
            
            // Process each record
            records.forEach(record => {
                const isCurrentMonth = record.creation >= monthStartDate;
                const isCurrentFY = record.creation >= fyStartDate;
                const isSameDepartment = record.department === frm.doc.department;
                
                const breakingAmount = flt(record.breaking_amount) || 0;
                const orgPlanValue = flt(record.org_plan_value) || 0;
                
                console.log(`Processing ${record.name}:`, {
                    isCurrentMonth,
                    isCurrentFY,
                    isSameDepartment,
                    stone_fault: record.stone_fault,
                    worker_fault: record.worker_fault
                });
                
                // Accumulate month and year summaries
                if (isSameDepartment) {
                    if (isCurrentMonth) {
                        if (record.stone_fault) {
                            currentMonthStoneFault.breaking_amount += breakingAmount;
                            currentMonthStoneFault.org_plan_value += orgPlanValue;
                            currentMonthStoneFault.count++;
                            console.log('Added to currentMonthStoneFault:', breakingAmount);
                        } else if (record.worker_fault) {
                            currentMonthWorkerFault.breaking_amount += breakingAmount;
                            currentMonthWorkerFault.org_plan_value += orgPlanValue;
                            currentMonthWorkerFault.count++;
                            console.log('Added to currentMonthWorkerFault:', breakingAmount);
                        } else {
                            // Default to worker fault if neither is checked
                            currentMonthWorkerFault.breaking_amount += breakingAmount;
                            currentMonthWorkerFault.org_plan_value += orgPlanValue;
                            currentMonthWorkerFault.count++;
                            console.log('Added to currentMonthWorkerFault (default):', breakingAmount);
                        }
                    }
                    
                    if (isCurrentFY) {
                        if (record.stone_fault) {
                            currentYearStoneFault.breaking_amount += breakingAmount;
                            currentYearStoneFault.org_plan_value += orgPlanValue;
                            currentYearStoneFault.count++;
                        } else if (record.worker_fault) {
                            currentYearWorkerFault.breaking_amount += breakingAmount;
                            currentYearWorkerFault.org_plan_value += orgPlanValue;
                            currentYearWorkerFault.count++;
                        } else {
                            currentYearWorkerFault.breaking_amount += breakingAmount;
                            currentYearWorkerFault.org_plan_value += orgPlanValue;
                            currentYearWorkerFault.count++;
                        }
                    }
                }
                
                // Fetch worker-specific stats
                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Stone Breaking Report",
                        name: record.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.article_workers) {
                            const recordOrgPlanValue = flt(r.message.org_plan_value) || 0;
                            
                            console.log(`Workers in ${record.name}:`, r.message.article_workers.map(w => w.employee_code));
                            
                            r.message.article_workers.forEach(worker => {
                                if (currentWorkers.includes(worker.employee_code)) {
                                    workerStats[worker.employee_code].breaking_amount += flt(worker.breaking_amount) || 0;
                                    workerStats[worker.employee_code].org_plan_value += recordOrgPlanValue;
                                    workerStats[worker.employee_code].count++;
                                    console.log(`Updated worker ${worker.employee_code}:`, workerStats[worker.employee_code]);
                                }
                            });
                        }
                        
                        processedRecords++;
                        
                        // Once all records processed, calculate percentages and display
                        if (processedRecords === totalRecordsToProcess) {
                            console.log('=== DEBUG: Final Summaries (before current doc) ===');
                            console.log('Month Stone Fault:', currentMonthStoneFault);
                            console.log('Month Worker Fault:', currentMonthWorkerFault);
                            console.log('Year Stone Fault:', currentYearStoneFault);
                            console.log('Year Worker Fault:', currentYearWorkerFault);
                            console.log('Worker Stats:', workerStats);
                            
                            finalizeSummaryCalculations(
                                frm,
                                currentMonthStoneFault,
                                currentMonthWorkerFault,
                                currentYearStoneFault,
                                currentYearWorkerFault,
                                workerStats,
                                monthStartDate,
                                fyStartDate
                            );
                        }
                    }
                });
            });
        }
    });
}

function finalizeSummaryCalculations(
    frm,
    currentMonthStoneFault,
    currentMonthWorkerFault,
    currentYearStoneFault,
    currentYearWorkerFault,
    workerStats,
    monthStartDate,
    fyStartDate
) {
    // Include current document data before finalizing
    includeCurrentDocument(
        frm,
        currentMonthStoneFault,
        currentMonthWorkerFault,
        currentYearStoneFault,
        currentYearWorkerFault,
        workerStats,
        monthStartDate,
        fyStartDate
    );
    
    // Calculate percentages for summaries
    const calculatePercentage = (summary) => {
        if (summary.org_plan_value > 0) {
            summary.breaking_percentage = (summary.breaking_amount / summary.org_plan_value) * 100;
        }
    };
    
    calculatePercentage(currentMonthStoneFault);
    calculatePercentage(currentMonthWorkerFault);
    calculatePercentage(currentYearStoneFault);
    calculatePercentage(currentYearWorkerFault);
    
    // Calculate percentages for workers
    Object.values(workerStats).forEach(worker => {
        if (worker.org_plan_value > 0) {
            worker.breaking_percentage = (worker.breaking_amount / worker.org_plan_value) * 100;
        }
    });
    
    console.log('=== DEBUG: Final Summaries (after current doc) ===');
    console.log('Month Stone Fault:', currentMonthStoneFault);
    console.log('Month Worker Fault:', currentMonthWorkerFault);
    console.log('Year Stone Fault:', currentYearStoneFault);
    console.log('Year Worker Fault:', currentYearWorkerFault);
    console.log('Worker Stats:', workerStats);
    
    // Store results in frm for access in display logic
    frm.breaking_summary_totals = {
        currentMonth: {
            stoneFault: currentMonthStoneFault,
            workerFault: currentMonthWorkerFault
        },
        currentYear: {
            stoneFault: currentYearStoneFault,
            workerFault: currentYearWorkerFault
        },
        workers: workerStats,
        dates: {
            monthStartDate: monthStartDate,
            fyStartDate: fyStartDate
        }
    };
    
    // Display the summary
    display_breaking_summary(frm);
}

// ============================================================================
// FRAPPE FORM EVENT HANDLERS
// ============================================================================

frappe.ui.form.on("Stone Breaking Report", {
    onload_post_render(frm) {
        // Generate a unique alphanumeric serial number
        const uniqueSerialNumber = 'LA-' + Math.random().toString(36).substr(2, 9).toUpperCase();
        frm.set_value('serial_number', uniqueSerialNumber);
        calculate_breaking_summary(frm);
    },
    
    refresh(frm) {
        // Calculate breaking summary whenever the form is opened/refreshed
        calculate_breaking_summary(frm);
        
        // Handle radio button field
        if (frm.fields_dict.html_field_name && frm.fields_dict.html_field_name.$wrapper) {
            // Update hidden field when radio is clicked
            frm.fields_dict.html_field_name.$wrapper.find('input[type="radio"]').on('change', function() {
                frm.set_value('tension_type_data_field', $(this).val());
            });

            // Check correct radio button on load
            const val = frm.doc.tension_type_data_field;
            if (val) {
                frm.fields_dict.html_field_name.$wrapper.find(`input[value="${val}"]`).prop('checked', true);
            }
        }

        // Apply custom styling with delay for DOM readiness
        setTimeout(() => {
            applySectionStyling(frm);
        }, 500);
    },

    article_workers_add(frm, cdt, cdn) {
        console.log("Row added");
        recalculate_breaking_amount(frm);
        calculate_breaking_summary(frm);
    },
    
    article_workers_remove(frm, cdt, cdn) {
        console.log("Row removed");
        recalculate_breaking_amount(frm);
        calculate_breaking_summary(frm);
    },

    org_plan_value(frm) {
        if (frm.doc.breaking_amount) {
            frm.set_value('revised_value', frm.doc.org_plan_value - frm.doc.breaking_amount);
            frm.set_value('breaking_percent', (frm.doc.breaking_amount / frm.doc.org_plan_value) * 100);
        }
        calculate_breaking_summary(frm);
    },

    breaking_amount(frm) {
        if (frm.doc.org_plan_value && frm.doc.breaking_amount) {
            frm.set_value('revised_value', frm.doc.org_plan_value - frm.doc.breaking_amount);
            frm.set_value('breaking_percent', (frm.doc.breaking_amount / frm.doc.org_plan_value) * 100);
            calculate_breaking_summary(frm);
        }
    },

    approval_date(frm) {
        frm.set_value('checked', !!frm.doc.approval_date);
    },

    department(frm) {
        // Recalculate whenever department changes
        calculate_breaking_summary(frm);
    },
    
    stone_fault(frm) {
        // Recalculate when fault type changes
        calculate_breaking_summary(frm);
    },
    
    worker_fault(frm) {
        // Recalculate when fault type changes
        calculate_breaking_summary(frm);
    }
});

// Child table handlers
frappe.ui.form.on("Stone Breaking Worker", {
    breaking_amount(frm, cdt, cdn) {
        recalculate_breaking_amount(frm);
        calculate_breaking_summary(frm);
    },
    
    employee_code(frm, cdt, cdn) {
        // Recalculate when worker is added or changed
        calculate_breaking_summary(frm);
    }
});

// ============================================================================
// STYLING FUNCTIONS
// ============================================================================

function applySectionStyling(frm) {
    const sectionStyle = {
        'background-color': 'rgba(245, 242, 221, 0.3)',
        'padding': '15px',
        'border-radius': '5px',
        'margin': '10px 0',
        'border': '4px solid #f8e7b3'
    };
    
    const fieldStyle = {
        'background-color': '#9edbf7',
        'border': '2px solid rgba(33, 150, 243, 0.3)',
        'border-radius': '2px',
        'font-weight': 'bold',
        'color': '#000'
    };
    
    // Apply section styling
    $('[data-fieldname="document_approval_section"]').closest('.form-section').css(sectionStyle);
    $('[data-fieldname="results_section"]').closest('.form-section').css(sectionStyle);
    
    // Apply field styling
    const styledFields = ['org_plan_value', 'breaking_percent', 'breaking_amount', 'revised_value'];
    styledFields.forEach(fieldName => {
        if (frm.fields_dict[fieldName]) {
            frm.fields_dict[fieldName].$wrapper.find('.control-input, .control-value').css(fieldStyle);
        }
    });
}