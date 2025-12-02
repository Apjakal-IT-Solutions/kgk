// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

// Toggle barcode analysis section
function toggleBarcodeAnalysis() {
	const barcodeList = document.querySelector('.barcode-list');
	const toggleIcon = document.querySelector('.barcode-toggle-icon');
	
	if (barcodeList.style.display === 'none') {
		barcodeList.style.display = 'block';
		toggleIcon.style.transform = 'rotate(0deg)';
		toggleIcon.textContent = '▼';
	} else {
		barcodeList.style.display = 'none';
		toggleIcon.style.transform = 'rotate(-90deg)';
		toggleIcon.textContent = '▶';
	}
}

frappe.query_reports["OCR Parcel Merge"] = {
	"filters": [
		{
			"fieldname": "parcel_name",
			"label": __("Parcel"),
			"fieldtype": "Link",
			"options": "Parcel",
			"width": "200px",
			"description": "Optional: Filter by specific Parcel (leave empty to include all Parcels)"
		},
		{
			"fieldname": "matching_mode",
			"label": __("Matching Mode"),
			"fieldtype": "Select",
			"options": "\nStrict\nFuzzy",
			"default": "Strict",
			"width": "120px",
			"description": "Strict: Exact matches only, Fuzzy: Similar matches (80%+ similarity)"
		}
		// ,
		// {
		// 	"fieldname": "lot_id_filter",
		// 	"label": __("Lot ID Filter"),
		// 	"fieldtype": "Data",
		// 	"width": "120px",
		// 	"description": "Filter by specific Lot ID pattern (optional)"
		// },
		// {
		// 	"fieldname": "barcode_filter",
		// 	"label": __("Barcode Filter"),
		// 	"fieldtype": "Data",
		// 	"width": "120px",
		// 	"description": "Filter by specific barcode pattern (optional)"
		// }
	],
	
	"onload": function(report) {
		// Handle route options for filtering
		if (frappe.route_options) {
			Object.keys(frappe.route_options).forEach(key => {
				if (report.get_filter(key)) {
					report.set_filter_value(key, frappe.route_options[key]);
				}
			});
			frappe.route_options = null;
			report.refresh();
		}
		
		// Add statistics section
		report.page.add_inner_message(__("OCR-Parcel Matching Analysis with Statistical Overview"));
		
		// Add chart container for statistics - only if it doesn't exist
		if ($('.chart-container').length === 0) {
			var chart_area = $(`
				<div class="chart-container" style="margin: 15px 0; padding: 15px; border: 1px solid #d1d8dd; border-radius: 4px;">
					<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
						<h5 style="margin: 0; color: #555;">Match Statistics</h5>
					</div>
					<div class="match-stats" style="display: flex; justify-content: space-around; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
						<div class="stat-card" style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px; min-width: 110px; flex: 1;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #007bff;">0</div>
							<div class="stat-label" style="font-size: 11px; color: #666;">Total OCR Records</div>
							<div class="stat-matched-count" style="font-size: 12px; color: #007bff; margin-top: 2px; font-weight: 500;">0 matched</div>
						</div>
						<div class="stat-card" style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px; min-width: 110px; flex: 1;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #6c757d;">0</div>
							<div class="stat-label" style="font-size: 11px; color: #666;">Total Parcel Records</div>
							<div class="stat-matched-count" style="font-size: 12px; color: #6c757d; margin-top: 2px; font-weight: 500;">0 matched</div>
						</div>
						<div class="stat-card matched-barcodes" style="text-align: center; padding: 10px; background: #d4edda; border-radius: 4px; min-width: 110px; flex: 1; border: 2px solid #28a745;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #155724;">0</div>
							<div class="stat-label" style="font-size: 11px; color: #155724; font-weight: 600;">Matched Barcodes</div>
							<div class="stat-sublabel" style="font-size: 10px; color: #666; margin-top: 2px;">Unique Values</div>
						</div>
					</div>
					<div class="chart-area" style="height: 250px;"></div>
					<div class="barcode-analysis" style="margin-top: 15px;">
						<h6 style="margin: 10px 0 5px 0; color: #555; font-size: 13px; cursor: pointer;" onclick="toggleBarcodeAnalysis()">
							<span class="barcode-toggle-icon" style="display: inline-block; transition: transform 0.3s;">▼</span> 
							Barcode Distribution (All Matches):
						</h6>
						<div class="barcode-list" style="max-height: 300px; overflow-y: auto; font-size: 11px; background: #f8f9fa; padding: 10px; border-radius: 4px;">
							<!-- Will be populated dynamically -->
						</div>
					</div>
				</div>
			`);
			report.page.main.prepend(chart_area);
			
			// Add click handlers for chart toggle buttons
		}
		
		// Store reference globally for easier access
		window.ocr_parcel_chart_area = $('.chart-container');
	},
	
	"formatter": function (value, row, column, data, default_formatter) {
		// Highlight match status - GREEN for matched, GRAY for unmatched
		if (column.fieldname === 'match_status') {
			if (value && value.includes('MATCHED')) {
				return `<span class="indicator green">${value}</span>`;
			} else if (value && value.includes('UNMATCHED')) {
				return `<span class="indicator gray">${value}</span>`;
			}
		}
		
		// Highlight match confidence
		if (column.fieldname === 'match_confidence') {
			const confidence = parseFloat(value);
			if (confidence >= 0.9) {
				return `<span style="background-color: #d4edda; padding: 2px 6px; border-radius: 3px; color: #155724;">${(confidence * 100).toFixed(1)}%</span>`;
			} else if (confidence >= 0.8) {
				return `<span style="background-color: #fff3cd; padding: 2px 6px; border-radius: 3px; color: #856404;">${(confidence * 100).toFixed(1)}%</span>`;
			} else if (confidence >= 0.5) {
				return `<span style="background-color: #f8d7da; padding: 2px 6px; border-radius: 3px; color: #721c24;">${(confidence * 100).toFixed(1)}%</span>`;
			} else if (confidence === 0) {
				return `<span style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px; color: #6c757d;">0%</span>`;
			}
		}
		
		// Highlight refined columns (AI-processed fields) - matches cumulative report style
		if (column.fieldname && column.fieldname.startsWith('refined_') && value) {
			return `<span style="background-color: #e3f2fd; padding: 2px 4px; border-radius: 3px; border-left: 3px solid #2196f3; font-weight: 500;">${value}</span>`;
		}
		
		// Highlight OCR Upload Name as clickable links
		if (column.fieldname === 'upload_name' && value) {
			return `<a href="#Form/OCR Data Upload/${value}" target="_blank">${value}</a>`;
		}
		
		// Show matching lot IDs and barcodes in a special color
		if ((column.fieldname.includes('lot_id') || column.fieldname === 'barcode' || column.fieldname === 'main_barcode') && value) {
			return `<span style="background-color: #f3e5f5; padding: 1px 3px; border-radius: 2px; font-weight: 500;">${value}</span>`;
		}
		
		return default_formatter(value, row, column, data);
	},
	
	"after_datatable_render": function(datatable_obj) {
		// CRITICAL DEBUG: Log how many rows are actually in the datatable
		console.log("=== DATATABLE RENDER DEBUG ===");
		console.log("Datatable row count:", datatable_obj ? datatable_obj.datamanager.rows.length : "NO DATATABLE");
		console.log("frappe.query_report.data length:", frappe.query_report.data ? frappe.query_report.data.length : "NO DATA");
		console.log("Expected: 480 rows (from chart stats)");
		console.log("=== END DEBUG ===");
		
		// Update statistics when data loads
		setTimeout(() => {
			try {
				// Check if we have valid filters before trying to get statistics
				if (!frappe.query_report || !frappe.query_report.get_values) {
					console.log("Query report not ready, skipping statistics");
					return;
				}
				
				var filters = frappe.query_report.get_values();
				
				// Always show the statistics area (data comes from database now)
				$('.chart-container').show();
				
				// Call API to get statistics (don't try to parse message)
				frappe.query_reports["OCR Parcel Merge"].update_statistics();
			} catch (error) {
				console.error("Error in after_datatable_render:", error);
				// Still try the API call as fallback
				try {
					frappe.query_reports["OCR Parcel Merge"].update_statistics();
				} catch (e) {
					console.error("API call fallback also failed:", e);
				}
			}
		}, 500);
	},
	
	"update_statistics": function() {
		// Get statistics from the report data or make a separate call with error handling
		try {
			// Use frappe.query_report directly since cur_report_item is not always available
			if (!frappe.query_report || !frappe.query_report.get_values) {
				console.log("query_report not ready, skipping statistics update");
				return;
			}
			
			var filters = frappe.query_report.get_values();
			
			frappe.call({
				method: "kgk_customisations.kgk_customisations.report.ocr_parcel_merge.ocr_parcel_merge.get_statistics",
				args: { filters: filters },
				callback: function(r) {
					try {
						if (r.message) {
							frappe.query_reports["OCR Parcel Merge"].render_statistics(r.message);
						}
					} catch (error) {
						console.error("Statistics render error:", error);
					}
				},
				error: function(error) {
					console.error("Statistics API error:", error);
				}
			});
		} catch (error) {
			console.error("Update statistics error:", error);
		}
	},
	
	"render_statistics": function(stats) {
		// Update the statistics cards with simplified barcode-focused counts
		var chart_area = $('.chart-container');
		if (chart_area.length > 0) {
			var cards = chart_area.find('.stat-card .stat-number');
			var matched_counts = chart_area.find('.stat-card .stat-matched-count');
			
			if (cards.length >= 3) {
				// Total OCR Records
				$(cards[0]).text(stats.total_ocr_records || 0).css('color', '#007bff');
				// OCR Matched Count - use UNIQUE count, not sum
				if (matched_counts.length >= 1) {
					var ocr_text = (stats.unique_ocr_matched || 0) + ' matched';
					if (stats.invalid_ocr_records > 0) {
						ocr_text += ', ' + stats.invalid_ocr_records + ' invalid';
					}
					$(matched_counts[0]).text(ocr_text).css('color', '#007bff');
				}
				
				// Total Parcel Records
				$(cards[1]).text(stats.total_parcel_records || 0).css('color', '#6c757d');
				// Parcel Matched Count - use UNIQUE count, not sum
				if (matched_counts.length >= 2) {
					var parcel_text = (stats.unique_parcel_matched || 0) + ' matched';
					if (stats.invalid_parcel_records > 0) {
						parcel_text += ', ' + stats.invalid_parcel_records + ' invalid';
					}
					$(matched_counts[1]).text(parcel_text).css('color', '#6c757d');
				}
				
				// Matched Barcodes (unique barcode values)
				$(cards[2]).text(stats.matched_barcode_count || 0).css('color', '#155724');
			}
			
			// Render barcode analysis if available
			if (stats.chart_data && stats.chart_data.barcode_analysis && stats.chart_data.barcode_analysis.length > 0) {
				var barcode_list = chart_area.find('.barcode-list');
				var barcode_section = chart_area.find('.barcode-analysis');
				
				barcode_list.empty();
				
				// Create table showing all barcodes with distribution
				var html = '<table style="width: 100%; border-collapse: collapse;">';
				html += '<thead><tr style="background: #dee2e6; font-weight: 600;">';
				html += '<th style="padding: 5px; text-align: left;">Barcode</th>';
				html += '<th style="padding: 5px; text-align: center;">OCR Count</th>';
				html += '<th style="padding: 5px; text-align: center;">Parcel Count</th>';
				html += '<th style="padding: 5px; text-align: center;">Total Rows</th>';
				html += '<th style="padding: 5px; text-align: center;">% of Total</th>';
				html += '</tr></thead><tbody>';
				
				stats.chart_data.barcode_analysis.forEach(function(item, index) {
					var bg = index % 2 === 0 ? '#ffffff' : '#f8f9fa';
					html += `<tr style="background: ${bg};">`;
					html += `<td style="padding: 5px; font-family: monospace;">${item.barcode}</td>`;
					html += `<td style="padding: 5px; text-align: center; color: #28a745; font-weight: 500;">${item.ocr_count}</td>`;
					html += `<td style="padding: 5px; text-align: center; color: #007bff; font-weight: 500;">${item.parcel_count}</td>`;
					html += `<td style="padding: 5px; text-align: center; color: #2e7d32; font-weight: 600;">${item.total_rows}</td>`;
					html += `<td style="padding: 5px; text-align: center; color: #856404; font-weight: 600;">${item.percentage}%</td>`;
					html += '</tr>';
				});
				
				html += '</tbody></table>';
				barcode_list.html(html);
				barcode_section.show();
			} else {
				chart_area.find('.barcode-analysis').hide();
			}
			
			// Render chart if chart data is available
			if (stats.chart_data) {
				frappe.query_reports["OCR Parcel Merge"].render_chart(stats.chart_data);
			}
		}
	},
	
	"render_chart": function(chart_data) {
		// Render the match statistics chart - simplified bar chart only
		try {
			var chart_container = $('.chart-container .chart-area')[0];
			if (!chart_container) return;
			
			// Clear previous chart
			$(chart_container).empty();
			
			// Check if chart_data is valid
			if (!chart_data) {
				$(chart_container).html('<div style="text-align: center; color: #666; padding: 20px;">No chart data available</div>');
				return;
			}
			
			// DEBUG: Log what values we're actually getting
			console.log("DEBUG: Chart data values:", {
				matched_ocr: chart_data.matched_ocr,
				matched_parcel: chart_data.matched_parcel,
				invalid_ocr: chart_data.invalid_ocr,
				invalid_parcel: chart_data.invalid_parcel,
				full_chart_data: chart_data
			});
			
			// Calculate total matched rows for explanation
			var total_matched_rows = chart_data.total_matched_rows || 0;
			
			// Create bar chart showing unique counts - 3 categories: Matched, Unmatched, Invalid
			new frappe.Chart(chart_container, {
				title: "Match Analysis (Unique Records)",
				data: {
					labels: ["OCR Records", "Parcel Records"],
					datasets: [
						{
							name: "Matched",
							values: [chart_data.matched_ocr, chart_data.matched_parcel]
						},
						{
							name: "Unmatched", 
							values: [chart_data.unmatched_ocr, chart_data.unmatched_parcel]
						},
						{
							name: "Invalid/No Barcode",
							values: [chart_data.invalid_ocr || 0, chart_data.invalid_parcel || 0]
						}
					]
				},
				type: 'bar',
				height: 200,
				colors: ['#28a745', '#dc3545', '#999999'],
				barOptions: {
					stacked: true,
					spaceRatio: 0.5
				},
				axisOptions: {
					xAxisMode: 'tick',
					xIsSeries: false
				},
				tooltipOptions: {
					formatTooltipY: d => d + " unique records"
				}
			});
			
			// Add explanation text showing relationship between unique counts and total rows
			var explanation = $(`
				<div style="text-align: center; color: #666; font-size: 10px; margin-top: 8px; padding: 0 10px;">
					Chart shows unique record counts. When matching barcodes appear in multiple records, the Cartesian product creates ${total_matched_rows} total rows displayed below. "Invalid/No Barcode" shows records filtered out due to missing or invalid barcode values.
				</div>
			`);
			$(chart_container).append(explanation);
			
		} catch (error) {
			console.error("Chart rendering error:", error);
			var chart_container = $('.chart-container .chart-area')[0];
			if (chart_container) {
				$(chart_container).html('<div style="text-align: center; color: #999; padding: 20px;">Chart temporarily unavailable</div>');
			}
		}
	}
};
