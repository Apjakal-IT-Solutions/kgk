// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Laser Approval Analysis"] = {
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
			fieldname: "tension_type",
			label: __("Tension Type"),
			fieldtype: "Select",
			options: "\nT1\nT2\nT3\nT4\nT5",
		},
		{
			fieldname: "plan_change_type",
			label: __("Plan Change Type"),
			fieldtype: "Select",
			options: "\nSafe LS\nPlan Change\nTilt",
		},
		{
			fieldname: "sawing_from",
			label: __("Sawing From"),
			fieldtype: "Select",
			options: "\nWater Jet\nQuazer",
		},
		{
			fieldname: "approval_type",
			label: __("Approval Type"),
			fieldtype: "Select",
			options: "\nSafe Sawing\nNo LS\nNormal Sawing\nAny Approved\nNot Approved",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Data",
		},
		{
			fieldname: "employee_status",
			label: __("Employee Status"),
			fieldtype: "Select",
			options: "\nYes\nNo",
		},
		{
			fieldname: "min_safe_sawing_pct",
			label: __("Min Safe Saw. %"),
			fieldtype: "Float",
		},
		{
			fieldname: "max_safe_sawing_pct",
			label: __("Max Safe Saw. %"),
			fieldtype: "Float",
		},
		{
			fieldname: "flag",
			label: __("Flag"),
			fieldtype: "Data",
		},
		{
			fieldname: "result",
			label: __("Result"),
			fieldtype: "Data",
		},
		{
			fieldname: "checked",
			label: __("Checked"),
			fieldtype: "Select",
			options: "\nChecked\nUnchecked",
		},
		{
			fieldname: "docstatus",
			label: __("Doc Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted",
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
		_laa_render(datatable_obj);
	},
};

function _laa_render(datatable_obj) {
	const data    = frappe.query_report.data    || [];
	const columns = frappe.query_report.columns || [];
	const summary = frappe.query_report.report_summary || [];

	const fmt_float = (v) => frappe.format(v || 0, { fieldtype: "Float", precision: 2 });
	const fmt_pct   = (v) => laa_flt(v).toFixed(2) + "%";

	// ── KPI cards ─────────────────────────────────────────────────────────────
	let kpi_html = "";
	if (summary.length) {
		kpi_html = `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">`;
		summary.forEach((s) => {
			const color = s.color || "#800000";
			const val   = s.datatype === "Percent" ? laa_flt(s.value).toFixed(2) + "%"
				: s.datatype === "Float"   ? laa_flt(s.value).toFixed(2)
				: s.value;
			kpi_html += `
			<div style="background:#fff;border:1px solid #d1d8dd;border-top:3px solid ${color};
			            border-radius:4px;padding:12px 18px;min-width:130px;flex:1">
				<div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">${s.label}</div>
				<div style="font-size:22px;font-weight:700;color:${color};margin-top:4px">${val}</div>
			</div>`;
		});
		kpi_html += `</div>`;
	}

	// ── Header ────────────────────────────────────────────────────────────────
	const col_defs = columns.filter(c => !c.hidden);
	let thead = `<thead><tr style="background:#f8f9fa">`;
	col_defs.forEach((c) => {
		const align = ["Float","Currency","Int","Percent"].includes(c.fieldtype) ? "right" : "left";
		thead += `<th style="${laa_th()}text-align:${align}">${c.label}</th>`;
	});
	thead += `</tr></thead>`;

	// ── Body ──────────────────────────────────────────────────────────────────
	const tension_colors = { "T1": "#e8f5e9", "T2": "#f1f8e9", "T3": "#fff9c4", "T4": "#ffe0b2", "T5": "#ffcdd2" };
	const status_styles  = {
		"Draft":     "background:#fff9c4;color:#795500;padding:1px 6px;border-radius:3px",
		"Submitted": "background:#d4f0dc;color:#1b5e20;padding:1px 6px;border-radius:3px",
	};

	let tbody = "<tbody>";
	data.forEach((row, ri) => {
		const rowBg    = ri % 2 === 0 ? "#fff" : "#f8f9fa";
		const highLoss = laa_flt(row.safe_sawing_percent) >= 5;
		const pctBg    = highLoss ? "#fde8e8" : "#d4f0dc";
		const tBg      = tension_colors[row.tension_type] || rowBg;

		tbody += `<tr style="background:${rowBg}">`;
		col_defs.forEach((c) => {
			const fn    = c.fieldname;
			let   val   = row[fn];
			let   bg    = rowBg;
			let   style = laa_td();

			if (fn === "name") {
				val = `<a href="/app/laser-approval/${encodeURIComponent(val)}" style="color:#800000">${val}</a>`;
			} else if (fn === "tension_type") {
				bg = tBg;
			} else if (fn === "safe_sawing_percent" || fn === "nols_percent") {
				val = fmt_pct(val);
				bg  = fn === "safe_sawing_percent" ? pctBg : rowBg;
				style += "text-align:right;";
			} else if (fn === "safe_sawing_amount" || fn === "nols_amount" || fn === "org_plan_value") {
				val = fmt_float(val); style += "text-align:right;";
			} else if (fn === "safe_sawing" || fn === "no_ls" || fn === "normal_sawing") {
				if (val) {
					val = `<span style="background:#f8f9fa;color:#800000;padding:1px 6px;border-radius:3px;font-size:11px">&#10003; ${c.label}</span>`;
					bg  = "#f8f9fa";
				} else {
					val = "";
				}
			} else if (fn === "checked_") {
				val = val ? `<span style="color:#800000;font-weight:bold">&#10003;</span>` : "";
			} else if (fn === "docstatus") {
				val = `<span style="${status_styles[val] || ""}">${val}</span>`;
			}

			tbody += `<td style="${style}background:${bg}">${val ?? ""}</td>`;
		});
		tbody += `</tr>`;
	});
	tbody += `</tbody>`;

	$(datatable_obj.wrapper).html(`
		<div style="padding:12px 4px">
			${kpi_html}
			<div style="overflow-x:auto">
				<table style="border-collapse:collapse;width:100%;font-size:13px;font-family:sans-serif">
					${thead}${tbody}
				</table>
			</div>
			<div style="margin-top:10px;font-size:11px;color:#aaa">
				&#11044; Safe Sawing % &ge; 5% highlighted red &nbsp;|&nbsp;
				&#11044; Tension colour: T1 low → T5 high &nbsp;|&nbsp;
				&#11044; Maroon badge = approved method
			</div>
		</div>`);
}

function laa_flt(v) { return parseFloat(v) || 0; }
function laa_th() { return "padding:10px 12px;color:#800000;background:#f8f9fa;border-bottom:2px solid #d1d8dd;white-space:nowrap;"; }
function laa_td() { return "padding:8px 12px;color:#444;border-bottom:1px solid #ebeff2;white-space:nowrap;"; }
