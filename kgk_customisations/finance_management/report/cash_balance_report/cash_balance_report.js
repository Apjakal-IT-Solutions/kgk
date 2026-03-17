// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Cash Balance Report"] = {
	filters: [
		{
			fieldname: "date_from",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "date_to",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Select",
			options: "\nDiamonds\nJewellery\nAgro",
			reqd: 1,
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: "\nUSD\nZAR\nBWP",
			reqd: 1,
		},
	],

	onload: function (report) {
		const _orig = report.render_datatable.bind(report);
		report.render_datatable = function () {
			report.datatable = null;
			_orig();
		};
	},

	after_datatable_render: function (datatable_obj) {
		const data     = frappe.query_report.data || [];
		const fval     = (name) => frappe.query_report.get_filter_value(name) || "";
		const company  = fval("company");
		const currency = fval("currency");

		const fmt = (v) =>
			frappe.format(v || 0, { fieldtype: "Currency" }, { always_show_decimals: true });

		const thead = `
			<thead>
				<tr style="background:#f8f9fa">
					<th style="${cbr_th()}text-align:left;min-width:100px">Date</th>
					<th style="${cbr_th()}text-align:center" colspan="3">${company} / ${currency}</th>
				</tr>
				<tr style="background:#f8f9fa">
					<th style="${cbr_th()}"></th>
					<th style="${cbr_th()}text-align:right">Cebo</th>
					<th style="${cbr_th()}text-align:right">Lore</th>
					<th style="${cbr_th()}text-align:right">Harsh</th>
				</tr>
			</thead>`;

		let tbody = "<tbody>";
		data.forEach((row, ri) => {
			const rowBg  = ri % 2 === 0 ? "#fff" : "#f8f9fa";
			const cellBg = row.tally ? "#d4f0dc" : "#fde8e8";
			tbody += `
				<tr style="background:${rowBg}">
					<td style="${cbr_td()}font-weight:500">${row.date}</td>
					<td style="${cbr_td()}text-align:right;background:${cellBg}">${fmt(row.basic)}</td>
					<td style="${cbr_td()}text-align:right;background:${cellBg}">${fmt(row.accountant)}</td>
					<td style="${cbr_td()}text-align:right;background:${cellBg}">${fmt(row.checker)}</td>
				</tr>`;
		});
		tbody += "</tbody>";

		$(datatable_obj.wrapper).html(`
			<div style="overflow-x:auto;padding:12px 4px">
				<table style="border-collapse:collapse;width:100%;font-size:13px;font-family:sans-serif">
					${thead}${tbody}
				</table>
			</div>`);
	},
};

function cbr_th() { return "padding:10px 12px;color:#800000;background:#f8f9fa;border-bottom:2px solid #d1d8dd;white-space:nowrap;"; }
function cbr_td() { return "padding:8px 12px;color:#444;border-bottom:1px solid #ebeff2;white-space:nowrap;"; }
