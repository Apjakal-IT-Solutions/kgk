// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Bank Balance Report"] = {
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
	],

	onload: function (report) {
		const _orig = report.render_datatable.bind(report);
		report.render_datatable = function () {
			report.datatable = null;
			_orig();
		};
	},

	after_datatable_render: function (datatable_obj) {
		const data    = frappe.query_report.data    || [];
		const columns = frappe.query_report.columns || [];

		const banks = [];
		columns.forEach((col) => {
			const m = (col.fieldname || "").match(/^bank_(\d+)_accountant$/);
			if (m) banks.push({ idx: m[1], label: (col.label || "").replace(/ Lore$/, "") });
		});

		const fmt = (v) =>
			frappe.format(v || 0, { fieldtype: "Currency" }, { always_show_decimals: true });

		let thead = `<thead><tr style="background:#f8f9fa">
			<th rowspan="2" style="${bbr_th()}text-align:left;min-width:100px">Date</th>`;
		banks.forEach((b) => {
			thead += `<th colspan="2" style="${bbr_th()}text-align:center">${b.label}</th>`;
		});
		thead += `</tr><tr style="background:#f8f9fa">`;
		banks.forEach(() => {
			thead += `<th style="${bbr_th()}text-align:right">Lore</th>
			          <th style="${bbr_th()}text-align:right">Harsh</th>`;
		});
		thead += `</tr></thead>`;

		let tbody = "<tbody>";
		data.forEach((row, ri) => {
			const rowBg = ri % 2 === 0 ? "#fff" : "#f8f9fa";
			tbody += `<tr style="background:${rowBg}">
				<td style="${bbr_td()}font-weight:500">${row.date}</td>`;
			banks.forEach((b) => {
				const acct    = row[`bank_${b.idx}_accountant`] || 0;
				const checker = row[`bank_${b.idx}_checker`]    || 0;
				const cellBg  = row[`tally_${b.idx}`] ? "#d4f0dc" : "#fde8e8";
				tbody += `<td style="${bbr_td()}text-align:right;background:${cellBg}">${fmt(acct)}</td>
				          <td style="${bbr_td()}text-align:right;background:${cellBg}">${fmt(checker)}</td>`;
			});
			tbody += `</tr>`;
		});
		tbody += `</tbody>`;

		$(datatable_obj.wrapper).html(`
			<div style="overflow-x:auto;padding:12px 4px">
				<table style="border-collapse:collapse;width:100%;font-size:13px;font-family:sans-serif">
					${thead}${tbody}
				</table>
			</div>`);
	},
};

function bbr_th() { return "padding:10px 12px;color:#800000;background:#f8f9fa;border-bottom:2px solid #d1d8dd;white-space:nowrap;"; }
function bbr_td() { return "padding:8px 12px;color:#444;border-bottom:1px solid #ebeff2;white-space:nowrap;"; }
