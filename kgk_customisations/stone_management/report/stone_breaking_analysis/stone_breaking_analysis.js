// Copyright (c) 2026, Apjakal IT Solutions and contributors
// For license information, please see license.txt

frappe.query_reports["Stone Breaking Analysis"] = {
	filters: [
		{ fieldname: "date_from",      label: __("From Date"),       fieldtype: "Date",   default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), reqd: 1 },
		{ fieldname: "date_to",        label: __("To Date"),         fieldtype: "Date",   default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "department",     label: __("Department"),      fieldtype: "Link",   options: "Department" },
		{ fieldname: "tension_type",   label: __("Tension Type"),    fieldtype: "Select", options: "\nt0\nt1\nt2\nt3\nt4\nt5" },
		{ fieldname: "fault_type",     label: __("Fault Type"),      fieldtype: "Select", options: "\nStone Fault\nWorker Fault\nBoth Faults\nAny Fault" },
		{ fieldname: "worker",         label: __("Worker"),          fieldtype: "Data" },
		{ fieldname: "worker_type",    label: __("Worker Type"),     fieldtype: "Select", options: "\nIndian\nLocal" },
		{ fieldname: "min_breaking_pct", label: __("Min Breaking %"), fieldtype: "Float" },
		{ fieldname: "max_breaking_pct", label: __("Max Breaking %"), fieldtype: "Float" },
		{ fieldname: "result",         label: __("Result"),          fieldtype: "Data" },
		{ fieldname: "checked",        label: __("Approval Status"), fieldtype: "Select", options: "\nChecked\nUnchecked" },
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
		const summary = frappe.query_report.report_summary || [];

		const fmt_float = (v) => frappe.format(v || 0, { fieldtype: "Float", precision: 2 });
		const fmt_pct   = (v) => (parseFloat(v) || 0).toFixed(2) + "%";

		// ── KPI cards ─────────────────────────────────────────────────────────
		let kpi_html = "";
		if (summary.length) {
			kpi_html = `<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">`;
			summary.forEach((s) => {
				const color = s.color || "#800000";
				const val   = s.datatype === "Percent" ? (parseFloat(s.value) || 0).toFixed(2) + "%"
					: s.datatype === "Float" ? (parseFloat(s.value) || 0).toFixed(2) : s.value;
				kpi_html += `
				<div style="background:#fff;border:1px solid #d1d8dd;border-top:3px solid ${color};
				            border-radius:4px;padding:12px 18px;min-width:140px;flex:1">
					<div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">${s.label}</div>
					<div style="font-size:22px;font-weight:700;color:${color};margin-top:4px">${val}</div>
				</div>`;
			});
			kpi_html += `</div>`;
		}

		// ── Header ────────────────────────────────────────────────────────────
		const col_defs = columns.filter(c => !c.hidden);
		let thead = `<thead><tr style="background:#f8f9fa">`;
		col_defs.forEach((c) => {
			const align = ["Float","Currency","Int","Percent"].includes(c.fieldtype) ? "right" : "left";
			thead += `<th style="${sba_th()}text-align:${align}">${c.label}</th>`;
		});
		thead += `</tr></thead>`;

		// ── Body ──────────────────────────────────────────────────────────────
		const tension_colors = { t0:"#e8f5e9", t1:"#f1f8e9", t2:"#fff9c4", t3:"#ffe0b2", t4:"#ffccbc", t5:"#ffcdd2" };

		let tbody = "<tbody>";
		data.forEach((row, ri) => {
			const rowBg = ri % 2 === 0 ? "#fff" : "#f8f9fa";
			const pctBg = (parseFloat(row.breaking_percent) || 0) >= 10 ? "#fde8e8" : "#d4f0dc";
			const tBg   = tension_colors[(row.tension_type || "").toLowerCase()] || rowBg;

			tbody += `<tr style="background:${rowBg}">`;
			col_defs.forEach((c) => {
				const fn = c.fieldname;
				let val  = row[fn];
				let bg   = rowBg;
				let style = sba_td();

				if      (fn === "breaking_percent")  { val = fmt_pct(val); bg = pctBg; }
				else if (fn === "tension_type")       { bg = tBg; val = (val || "").toUpperCase(); }
				else if (fn === "breaking_amount" || fn === "org_plan_value") { val = fmt_float(val); style += "text-align:right;"; }
				else if (["stone_fault","worker_fault","checked"].includes(fn)) { val = val ? `<span style="color:#800000;font-weight:bold">&#10003;</span>` : ""; }
				else if (fn === "name") { val = `<a href="/app/stone-breaking-report/${encodeURIComponent(val)}" style="color:#800000">${val}</a>`; }

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
					&#11044; Breaking % &ge; 10% highlighted red &nbsp;|&nbsp; &#11044; Tension colour: T0 low → T5 high
				</div>
			</div>`);
	},
};

function sba_th() { return "padding:10px 12px;color:#800000;background:#f8f9fa;border-bottom:2px solid #d1d8dd;white-space:nowrap;"; }
function sba_td() { return "padding:8px 12px;color:#444;border-bottom:1px solid #ebeff2;white-space:nowrap;"; }
