// Copyright (c) 2025, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["OCR Parcel Merge"] = {
	"filters": [
		{
			"fieldname": "parcel_file",
			"label": __("Parcel File"),
			"fieldtype": "Attach",
			"width": "200px",
			"reqd": 1,
			"description": "Upload Excel file containing Parcel data with barcode column for matching"
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
						<div class="chart-toggle" style="display: flex; gap: 10px;">
							<button class="btn btn-xs chart-toggle-btn active" data-type="bar" style="background: #007bff; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px;">Bar Chart</button>
							<button class="btn btn-xs chart-toggle-btn" data-type="pie" style="background: #f8f9fa; color: #495057; border: 1px solid #dee2e6; padding: 4px 8px; border-radius: 3px; font-size: 11px;">Pie Chart</button>
						</div>
					</div>
					<div class="match-stats" style="display: flex; justify-content: space-around; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
						<div class="stat-card" style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px; min-width: 110px; flex: 1;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #007bff;">0</div>
							<div class="stat-label" style="font-size: 11px; color: #666;">Total OCR</div>
						</div>
						<div class="stat-card ocr-matched" style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px; min-width: 110px; flex: 1;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #28a745;">0</div>
							<div class="stat-secondary" style="font-size: 13px; color: #6c757d; margin-top: 2px;">0 rows</div>
							<div class="stat-label" style="font-size: 11px; color: #666;">OCR Matched</div>
						</div>
						<div class="stat-card" style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px; min-width: 110px; flex: 1;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #6c757d;">0</div>
							<div class="stat-label" style="font-size: 11px; color: #666;">Total Parcel</div>
						</div>
						<div class="stat-card parcel-matched" style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 4px; min-width: 110px; flex: 1;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #28a745;">0</div>
							<div class="stat-secondary" style="font-size: 13px; color: #6c757d; margin-top: 2px;">0 rows</div>
							<div class="stat-label" style="font-size: 11px; color: #666;">Parcel Matched</div>
						</div>
						<div class="stat-card total-rows" style="text-align: center; padding: 10px; background: #e8f5e9; border-radius: 4px; min-width: 110px; flex: 1; border: 2px solid #28a745;">
							<div class="stat-number" style="font-size: 24px; font-weight: bold; color: #2e7d32;">0</div>
							<div class="stat-label" style="font-size: 11px; color: #2e7d32; font-weight: 600;">Total Rows</div>
							<div class="stat-sublabel" style="font-size: 10px; color: #666; margin-top: 2px;">Cartesian Product</div>
						</div>
					</div>
					<div class="chart-area" style="height: 250px;"></div>
				</div>
			`);
			report.page.main.prepend(chart_area);
			
			// Add click handlers for chart toggle buttons
			$('.chart-toggle-btn').on('click', function() {
				var chartType = $(this).data('type');
				
				// Update button styles
				$('.chart-toggle-btn').removeClass('active').css({
					'background': '#f8f9fa',
					'color': '#495057'
				});
				$(this).addClass('active').css({
					'background': '#007bff',
					'color': 'white'
				});
				
				// Store current chart type and re-render
				window.current_chart_type = chartType;
				
				// Re-render chart with new type if we have data
				if (window.current_chart_data) {
					frappe.query_reports["OCR Parcel Merge"].render_chart(window.current_chart_data, chartType);
				}
			});
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
		// Update statistics when data loads using multiple approaches
		setTimeout(() => {
			try {
				// Check if we have valid filters before trying to extract statistics
				if (!frappe.query_report || !frappe.query_report.get_values) {
					console.log("Query report not ready, skipping statistics");
					return;
				}
				
				var filters = frappe.query_report.get_values();
				if (!filters || !filters.parcel_file) {
					console.log("No parcel file selected, skipping statistics");
					// Hide the statistics area if no file is selected
					$('.chart-container').hide();
					return;
				}
				
				// Show the statistics area if we have a parcel file
				$('.chart-container').show();
				
				// Try to extract statistics from the report message
				var report_message = '';
				
				// Check various places for the report message safely
				if (frappe.query_report && frappe.query_report.message) {
					report_message = frappe.query_report.message;
				} else if (frappe.query_report && frappe.query_report.page && frappe.query_report.page.page) {
					var msgprint = frappe.query_report.page.page.find('.msgprint');
					if (msgprint.length > 0) {
						report_message = msgprint.text();
					}
				}
				
				// Also try to find message in the DOM
				if (!report_message) {
					var msg_elements = $('.layout-main-section .msgprint, .frappe-page-content .msgprint, .page-content .msgprint');
					if (msg_elements.length > 0) {
						report_message = msg_elements.last().text();
					}
				}
				
				console.log("Report message found:", report_message);
				
				// Parse the message for statistics
				var stats_match = report_message.match(/(\d+) matches found from (\d+) OCR records and (\d+) parcel records/);
				
				if (stats_match) {
					var matched_count = parseInt(stats_match[1]);
					var total_ocr = parseInt(stats_match[2]);
					var total_parcel = parseInt(stats_match[3]);
					
					var stats = {
						total_ocr_records: total_ocr,
						matched_ocr_records: matched_count,
						unmatched_ocr_records: total_ocr - matched_count,
						total_parcel_records: total_parcel,
						matched_parcel_records: matched_count,
						unmatched_parcel_records: total_parcel - matched_count,
						chart_data: {
							matched_ocr: matched_count,
							unmatched_ocr: total_ocr - matched_count,
							matched_parcel: matched_count,
							unmatched_parcel: total_parcel - matched_count
						}
					};
					
					console.log("Extracted statistics:", stats);
					frappe.query_reports["OCR Parcel Merge"].render_statistics(stats);
				} else {
					console.log("Could not parse statistics from message, trying API call");
					// Fallback to API call
					frappe.query_reports["OCR Parcel Merge"].update_statistics();
				}
			} catch (error) {
				console.error("Error in after_datatable_render:", error);
				// Still try the API call as final fallback
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
			if (!filters || !filters.parcel_file) {
				console.log("No parcel file in filters, skipping statistics update");
				return;
			}
			
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
		// Update the statistics cards with unique counts and total row count
		var chart_area = $('.chart-container');
		if (chart_area.length > 0) {
			var cards = chart_area.find('.stat-card .stat-number');
			if (cards.length >= 5) {
				// Total OCR
				$(cards[0]).text(stats.total_ocr_records || 0).css('color', '#007bff');
				
				// OCR Matched (unique) with total rows
				$(cards[1]).text(stats.matched_ocr_records || 0).css('color', '#28a745');
				var ocr_secondary = chart_area.find('.stat-card.ocr-matched .stat-secondary');
				if (ocr_secondary.length > 0 && stats.chart_data && stats.chart_data.total_matched_rows) {
					ocr_secondary.text(stats.chart_data.total_matched_rows + ' rows');
				}
				
				// Total Parcel
				$(cards[2]).text(stats.total_parcel_records || 0).css('color', '#6c757d');
				
				// Parcel Matched (unique) with total rows
				$(cards[3]).text(stats.matched_parcel_records || 0).css('color', '#28a745');
				var parcel_secondary = chart_area.find('.stat-card.parcel-matched .stat-secondary');
				if (parcel_secondary.length > 0 && stats.chart_data && stats.chart_data.total_matched_rows) {
					parcel_secondary.text(stats.chart_data.total_matched_rows + ' rows');
				}
				
				// Total Matched Rows (Cartesian product)
				$(cards[4]).text((stats.chart_data && stats.chart_data.total_matched_rows) || 0).css('color', '#2e7d32');
			}
			
			// Render chart if chart data is available
			if (stats.chart_data) {
				frappe.query_reports["OCR Parcel Merge"].render_chart(stats.chart_data);
			}
		}
	},
	
	"render_chart": function(chart_data, chart_type) {
		// Render the match statistics chart with enhanced overlay showing unique counts and total rows
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
			
			// Store chart data globally for chart type switching
			window.current_chart_data = chart_data;
			
			// Use provided chart type or default to bar
			chart_type = chart_type || window.current_chart_type || 'bar';
			window.current_chart_type = chart_type;
			
			// Calculate values for charts
			var total_ocr = chart_data.matched_ocr + chart_data.unmatched_ocr;
			var total_parcel = chart_data.matched_parcel + chart_data.unmatched_parcel;
			var ocr_match_pct = total_ocr > 0 ? (chart_data.matched_ocr / total_ocr * 100) : 0;
			var parcel_match_pct = total_parcel > 0 ? (chart_data.matched_parcel / total_parcel * 100) : 0;
			var total_matched_rows = chart_data.total_matched_rows || 0;
			
			if (chart_type === 'pie') {
				// Create pie chart showing overall match distribution with total rows annotation
				var total_records = total_ocr + total_parcel;
				var total_matched = chart_data.matched_ocr + chart_data.matched_parcel;
				var total_unmatched = total_records - total_matched;
				
				// Create container for chart and annotation
				var wrapper = $('<div style="position: relative; height: 200px;"></div>');
				$(chart_container).append(wrapper);
				
				new frappe.Chart(wrapper[0], {
					title: "Overall Match Distribution",
					data: {
						labels: ["Matched", "Unmatched"],
						datasets: [
							{
								values: [total_matched, total_unmatched]
							}
						]
					},
					type: 'pie',
					height: 200,
					colors: ['#28a745', '#dc3545']
				});
				
				// Add annotation overlay for total rows
				if (total_matched_rows > 0) {
					var annotation = $(`
						<div style="position: absolute; top: 10px; right: 10px; background: rgba(46, 125, 50, 0.9); color: white; 
							padding: 8px 12px; border-radius: 4px; font-size: 11px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
							Total Rows: ${total_matched_rows}
							<div style="font-size: 9px; font-weight: 400; margin-top: 2px;">Cartesian Product</div>
						</div>
					`);
					wrapper.append(annotation);
				}
			} else {
				// Create bar chart with enhanced overlay showing unique counts + total rows
				// Option C: Single coherent chart with total rows as annotation
				
				// Create container for chart and annotation
				var wrapper = $('<div style="position: relative; height: 200px;"></div>');
				$(chart_container).append(wrapper);
				
				new frappe.Chart(wrapper[0], {
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
							}
						]
					},
					type: 'bar',
					height: 200,
					colors: ['#28a745', '#dc3545'],
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
				
				// Add annotation overlay showing total rows (Cartesian product)
				if (total_matched_rows > 0) {
					var annotation = $(`
						<div style="position: absolute; top: 10px; right: 10px; background: rgba(46, 125, 50, 0.9); color: white; 
							padding: 10px 14px; border-radius: 4px; font-size: 12px; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
							<div style="font-size: 18px; font-weight: bold;">${total_matched_rows}</div>
							<div style="font-size: 10px; font-weight: 400; margin-top: 2px;">Total Matched Rows</div>
							<div style="font-size: 9px; font-weight: 300; margin-top: 1px; opacity: 0.9;">Cartesian Product</div>
						</div>
					`);
					wrapper.append(annotation);
				}
				
				// Add subtle text below chart explaining the metrics
				var explanation = $(`
					<div style="text-align: center; color: #666; font-size: 10px; margin-top: 8px; padding: 0 10px;">
						Chart shows unique record counts. Total rows (${total_matched_rows}) includes all combinations from matching barcodes.
					</div>
				`);
				$(chart_container).append(explanation);
			}
		} catch (error) {
			console.error("Chart rendering error:", error);
			var chart_container = $('.chart-container .chart-area')[0];
			if (chart_container) {
				$(chart_container).html('<div style="text-align: center; color: #999; padding: 20px;">Chart temporarily unavailable</div>');
			}
		}
	}
};
