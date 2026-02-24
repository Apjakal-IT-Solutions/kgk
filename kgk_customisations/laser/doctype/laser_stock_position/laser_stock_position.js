frappe.ui.form.on("Laser Stock Position", {
	refresh(frm) {
		calculate_pcs_total(frm);
	},
	
	validate(frm) {
		calculate_pcs_total(frm);
	},
	
	laser_stock_item_table_add: function(frm) {
		calculate_pcs_total(frm);
	},
	
	laser_stock_item_table_remove: function(frm) {
		calculate_pcs_total(frm);
	}
});

frappe.ui.form.on("Laser Stock Position Item", {
	pcs: function(frm) {
		calculate_pcs_total(frm);
	}
});

function calculate_pcs_total(frm) {
	let total_pcs = 0;
	console.log("Calculating PCS total...");
	
	if (frm.doc.laser_stock_item_table) {
		frm.doc.laser_stock_item_table.forEach(function(row) {
			if (row.pcs && !isNaN(row.pcs)) {
				total_pcs += parseInt(row.pcs) || 0;
				console.log(`Adding ${row.pcs} from row ${row.name}, total so far: ${total_pcs}`);
			}
		});
	}
	
	frm.set_value('pcs_total', total_pcs);
	frm.refresh_field('pcs_total');
}