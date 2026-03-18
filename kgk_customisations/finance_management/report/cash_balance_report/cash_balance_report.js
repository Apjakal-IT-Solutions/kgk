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
			options: "All\nDiamonds\nJewellery\nAgro",
			default: "All",
			reqd: 1,
		},
		{
			fieldname: "currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: "All\nUSD\nZAR\nBWP",
			default: "All",
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
		const data = frappe.query_report.data || [];

		const fmt = (v, fieldtype) =>
			fieldtype === "Currency"
				? frappe.format(v || 0, { fieldtype: "Currency" }, { always_show_decimals: true })
				: (v || "");

		const allCols = frappe.query_report.columns || [];
		const cols    = allCols.filter(c => !c.hidden);
		const dateCol = cols[0];
		const valCols = cols.slice(1);

		// Alternating palette per group: [header-bg, tally-match-bg, tally-mismatch-bg]
		const GROUP_PALETTE = [
			{ hdr: "#dce8ff", match: "#d4f0dc", mismatch: "#fde8e8" },
			{ hdr: "#fff3cd", match: "#c8e8d0", mismatch: "#ffd6d6" },
		];

		// Group value columns by their `group` label (preserving order)
		const groups = [];
		valCols.forEach(c => {
			const gLabel = c.group || "";
			let g = groups.find(g => g.label === gLabel);
			if (!g) {
				g = { label: gLabel, cols: [], index: groups.length };
				groups.push(g);
			}
			g.cols.push(c);
		});

		// Build fieldname → group-index lookup for O(1) access in tbody
		const colGi = {};
		groups.forEach(g => g.cols.forEach(c => { colGi[c.fieldname] = g.index; }));

		const row1 = groups.map(g => {
			const pal = GROUP_PALETTE[g.index % 2];
			return `<th style="${cbr_th()}text-align:center;background:${pal.hdr};border-left:2px solid #c8d0dc" colspan="${g.cols.length}">${g.label}</th>`;
		}).join("");

		const row2 = valCols.map((c, ci) => {
			const pal    = GROUP_PALETTE[colGi[c.fieldname] % 2];
			const isFirst = ci === 0 || colGi[c.fieldname] !== colGi[valCols[ci - 1].fieldname];
			const border  = isFirst ? "border-left:2px solid #c8d0dc;" : "";
			return `<th style="${cbr_th()}text-align:right;background:${pal.hdr};${border}">${c.label}</th>`;
		}).join("");

		const thead = `
			<thead>
				<tr style="background:#f8f9fa">
					<th style="${cbr_th()}text-align:left;min-width:100px">${dateCol.label}</th>
					${row1}
				</tr>
				<tr style="background:#f8f9fa">
					<th style="${cbr_th()}"></th>${row2}
				</tr>
			</thead>`;

		let tbody = "<tbody>";
		data.forEach((row, ri) => {
			const rowBg = ri % 2 === 0 ? "#fff" : "#f8f9fa";
			tbody += `
				<tr style="background:${rowBg}">
					<td style="${cbr_td()}font-weight:500">${row[dateCol.fieldname] || ""}</td>
					${valCols.map((c, ci) => {
						const pal     = GROUP_PALETTE[colGi[c.fieldname] % 2];
						const cellBg  = row[c.tally_field] ? pal.match : pal.mismatch;
						const isFirst = ci === 0 || colGi[c.fieldname] !== colGi[valCols[ci - 1].fieldname];
						const border  = isFirst ? "border-left:2px solid #c8d0dc;" : "";
						return `<td style="${cbr_td()}text-align:right;background:${cellBg};${border}">${fmt(row[c.fieldname], c.fieldtype)}</td>`;
					}).join("")}
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
