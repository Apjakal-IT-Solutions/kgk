// Helper to always sync radio UI with hidden field
function syncRadioButtonWithValue(frm) {
    if (frm.fields_dict.tension_type && frm.fields_dict.tension_type.$wrapper) {
        const val = frm.doc.tension_type_data_field;
        console.log('[Stone Breaking Report] Syncing radio buttons. Saved value:', val);
        frm.fields_dict.tension_type.$wrapper.find('input[type="radio"]').each(function() {
            if ($(this).val() === val) {
                $(this).prop('checked', true);
                console.log(`[Stone Breaking Report] Checked radio: value=${val}`);
            } else {
                $(this).prop('checked', false);
            }
        });
        // Update hidden field when radio is clicked
        frm.fields_dict.tension_type.$wrapper.find('input[type="radio"]').off('change.stone_breaking_radio').on('change.stone_breaking_radio', function() {
            const selected = $(this).val();
            console.log(`[Stone Breaking Report] Radio clicked. Setting hidden field to: ${selected}`);
            frm.set_value('tension_type_data_field', selected);
        });
    } else {
        console.warn('[Stone Breaking Report] Radio button wrapper not found.');
    }
}
// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getBaseLotId(name) {
    // Strip -b, -c, …, -z, -aa, -ab, … suffix to get the original lot ID
    return (name || '').replace(/-[a-z]+$/, '');
}

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


function updateWorkerTables(wrapper, monthWorkers, ytdWorkers) {
    // Build a single grouped table: Month sub-header + month worker rows, then YTD sub-header + YTD worker rows
    let html = '';

    // --- Month section ---
    const hasMonthWorkers = monthWorkers && Object.keys(monthWorkers).length > 0;
    html += `<tr class="worker-section-row worker-subheader" style="border-bottom: 1px solid #ebeff2;">
        <td colspan="4" style="padding: 10px; color: #444; font-weight: bold;">Month</td>
    </tr>`;
    if (hasMonthWorkers) {
        Object.values(monthWorkers).forEach(worker => {
            let label = worker.worker_name
                ? `${worker.worker_name} (${worker.employee_code || ''})`
                : (worker.employee_code || 'N/A');
            html += `
                <tr class="worker-section-row" style="border-bottom: 1px solid #ebeff2;">
                    <td style="padding: 10px 10px 10px 20px; color: #444;">${label}</td>
                    <td style="padding: 10px; color: #444;">${formatNumber(worker.breaking_amount)}</td>
                    <td style="padding: 10px; color: #444;">${formatNumber(worker.org_plan_value)}</td>
                    <td style="padding: 10px; color: #444;">${formatPercent(worker.breaking_percentage)}</td>
                </tr>`;
        });
    } else {
        html += `<tr class="worker-section-row">
            <td colspan="4" style="padding: 10px 10px 10px 20px; text-align: center; color: #999;">No worker data available for Month</td>
        </tr>`;
    }

    // --- Year To Date section ---
    const hasYtdWorkers = ytdWorkers && Object.keys(ytdWorkers).length > 0;
    html += `<tr class="worker-section-row worker-subheader" style="border-bottom: 1px solid #ebeff2;">
        <td colspan="4" style="padding: 10px; color: #444; font-weight: bold;">Year To Date</td>
    </tr>`;
    if (hasYtdWorkers) {
        Object.values(ytdWorkers).forEach(worker => {
            let label = worker.worker_name
                ? `${worker.worker_name} (${worker.employee_code || ''})`
                : (worker.employee_code || 'N/A');
            html += `
                <tr class="worker-section-row" style="border-bottom: 1px solid #ebeff2;">
                    <td style="padding: 10px 10px 10px 20px; color: #444;">${label}</td>
                    <td style="padding: 10px; color: #444;">${formatNumber(worker.breaking_amount)}</td>
                    <td style="padding: 10px; color: #444;">${formatNumber(worker.org_plan_value)}</td>
                    <td style="padding: 10px; color: #444;">${formatPercent(worker.breaking_percentage)}</td>
                </tr>`;
        });
    } else {
        html += `<tr class="worker-section-row">
            <td colspan="4" style="padding: 10px 10px 10px 20px; text-align: center; color: #999;">No worker data available for YTD</td>
        </tr>`;
    }

    // Clean up: remove all previously inserted worker section rows
    wrapper.find('.worker-section-row').remove();
    // Remove old-style placeholders/headers if still present from legacy template
    wrapper.find('#worker_table_placeholder_month, #worker_table_placeholder_ytd').remove();
    wrapper.find('.worker-data-row-month, .worker-data-row-ytd, .worker-data-row').remove();

    const placeholder = wrapper.find('#worker_table_placeholder');
    if (placeholder.length) {
        placeholder.replaceWith(html);
    } else {
        // Append after the Employee header row
        const headerRow = wrapper.find('th').filter(function() {
            return $(this).text().trim() === 'Employee';
        }).closest('tr').last();
        if (headerRow.length) {
            headerRow.after(html);
        }
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
    
    // Prepare per-worker month and YTD data — only for workers in the current document
    const monthWorkers = {};
    const ytdWorkers = {};
    const currentWorkerCodes = (frm.doc.article_workers || []).map(w => w.employee_code).filter(Boolean);
    if (summary && summary.workers) {
        Object.values(summary.workers).forEach(worker => {
            if (worker && worker.employee_code && currentWorkerCodes.includes(worker.employee_code)) {
                if (worker.month && typeof worker.month === 'object') {
                    monthWorkers[worker.employee_code] = {
                        ...worker.month,
                        employee_code: worker.employee_code,
                        worker_name: worker.worker_name || ''
                    };
                }
                if (worker.ytd && typeof worker.ytd === 'object') {
                    ytdWorkers[worker.employee_code] = {
                        ...worker.ytd,
                        employee_code: worker.employee_code,
                        worker_name: worker.worker_name || ''
                    };
                }
            }
        });
    }
    updateWorkerTables(wrapper, monthWorkers, ytdWorkers);
    
    // Update month summary
    updateSummarySection(wrapper, summary.currentMonth, '');
    
    // Update YTD summary
    updateSummarySection(wrapper, summary.currentYear, 'ytd_');
}

// ============================================================================
// CURRENT DOCUMENT INCLUSION
// ============================================================================

function includeCurrentDocument(frm, summary) {
    // Only include if document has required data
    if (!frm.doc.breaking_amount || !frm.doc.org_plan_value) {
        return;
    }

    const breakingAmount = flt(frm.doc.breaking_amount) || 0;
    const orgPlanValue = flt(frm.doc.org_plan_value) || 0;
    const docDate = frm.doc.date || frappe.datetime.get_today();
    const today = frappe.datetime.get_today();
    const todayObj = frappe.datetime.str_to_obj(today);
    const currentMonth = todayObj.getMonth() + 1;
    const currentYear = todayObj.getFullYear();
    const fyStartYear = currentMonth >= 4 ? currentYear : currentYear - 1;
    const fyStartDate = `${fyStartYear}-04-01`;
    const monthStartDate = `${currentYear}-${String(currentMonth).padStart(2, '0')}-01`;

    const isCurrentMonth = docDate >= monthStartDate;
    const isCurrentFY = docDate >= fyStartDate;

    const bucket = frm.doc.stone_fault ? 'stoneFault' : 'workerFault';
    const baseLot = getBaseLotId(frm.doc.name);

    // Retrieve counted lot sets from server response
    const countedLots = summary.counted_lots || {};
    const seenYear = new Set(countedLots.year || []);
    const seenMonth = new Set(countedLots.month || []);
    const workerSeenYear = countedLots.worker_year || {};
    const workerSeenMonth = countedLots.worker_month || {};

    // Add to year summary — org_plan_value only if lot not already counted
    if (isCurrentFY) {
        summary.currentYear[bucket].breaking_amount += breakingAmount;
        if (!seenYear.has(baseLot)) {
            seenYear.add(baseLot);
            summary.currentYear[bucket].org_plan_value += orgPlanValue;
        }
    }

    // Add to month summary
    if (isCurrentMonth) {
        summary.currentMonth[bucket].breaking_amount += breakingAmount;
        if (!seenMonth.has(baseLot)) {
            seenMonth.add(baseLot);
            summary.currentMonth[bucket].org_plan_value += orgPlanValue;
        }
    }

    // Add current document's workers to worker stats
    if (frm.doc.article_workers && frm.doc.article_workers.length > 0) {
        frm.doc.article_workers.forEach(worker => {
            const code = worker.employee_code;
            if (!code) return;
            if (!summary.workers[code]) {
                summary.workers[code] = {
                    employee_code: code,
                    worker_name: worker.worker_name || '',
                    month: { breaking_amount: 0, org_plan_value: 0, breaking_percentage: 0 },
                    ytd: { breaking_amount: 0, org_plan_value: 0, breaking_percentage: 0 }
                };
            }
            // Per-worker lot dedup
            const wSeenYear = new Set(workerSeenYear[code] || []);
            const wSeenMonth = new Set(workerSeenMonth[code] || []);

            if (isCurrentFY) {
                summary.workers[code].ytd.breaking_amount += flt(worker.breaking_amount) || 0;
                if (!wSeenYear.has(baseLot)) {
                    summary.workers[code].ytd.org_plan_value += orgPlanValue;
                }
            }
            if (isCurrentMonth) {
                summary.workers[code].month.breaking_amount += flt(worker.breaking_amount) || 0;
                if (!wSeenMonth.has(baseLot)) {
                    summary.workers[code].month.org_plan_value += orgPlanValue;
                }
            }
        });
    }

    // Recalculate percentages
    const recalc = (bucket) => {
        bucket.breaking_percentage = bucket.org_plan_value > 0
            ? (bucket.breaking_amount / bucket.org_plan_value) * 100
            : 0;
    };
    recalc(summary.currentMonth.stoneFault);
    recalc(summary.currentMonth.workerFault);
    recalc(summary.currentYear.stoneFault);
    recalc(summary.currentYear.workerFault);
    Object.values(summary.workers).forEach(w => {
        recalc(w.month);
        recalc(w.ytd);
    });
}

// ============================================================================
// SUMMARY CALCULATION FUNCTION
// ============================================================================

function calculate_breaking_summary(frm) {
    if (!frm.doc.department) {
        console.log("Department not set, skipping summary calculation");
        return;
    }

    frappe.call({
        method: "kgk_customisations.stone_management.doctype.stone_breaking_report.stone_breaking_report.get_breaking_summary",
        args: {
            department: frm.doc.department,
            current_doc_name: frm.doc.name || null
        },
        callback: function(response) {
            if (!response.message) {
                console.log('No summary data returned');
                return;
            }

            const summary = response.message;

            // Include the current (possibly unsaved) document
            includeCurrentDocument(frm, summary);

            // Store and display
            frm.breaking_summary_totals = summary;
            display_breaking_summary(frm);
        }
    });
}

// ============================================================================
// FRAPPE FORM EVENT HANDLERS
// ============================================================================

frappe.ui.form.on("Stone Breaking Report", {
    after_save(frm) {
        syncRadioButtonWithValue(frm);
    },
    onload_post_render(frm) {
        // Generate a unique alphanumeric serial number
        const uniqueSerialNumber = 'LA-' + Math.random().toString(36).substr(2, 9).toUpperCase();
        frm.set_value('serial_number', uniqueSerialNumber);
        
        calculate_breaking_summary(frm);
        updateDepartmentHeading(frm);
    },
    
    refresh(frm) {
        calculate_breaking_summary(frm);
        syncRadioButtonWithValue(frm);
        setTimeout(() => {
            applySectionStyling(frm);
        }, 500);
    },
    tension_type_data_field(frm) {
        syncRadioButtonWithValue(frm);
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

    remark(frm) {
        frm.set_value('checked', !! frm.doc.remark);
    },

    department(frm) {
        // Recalculate whenever department changes
        calculate_breaking_summary(frm);
        updateDepartmentHeading(frm);
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

function updateDepartmentHeading(frm) {
    const department = frm.doc.department || "Department";
    frm.fields_dict.breaking_report.$wrapper.find('#department_heading').text(department);
}