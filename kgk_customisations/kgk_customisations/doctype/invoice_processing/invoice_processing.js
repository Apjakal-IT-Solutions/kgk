frappe.ui.form.on("Invoice Processing", {
    item_description: function(frm) {
        let description = frm.doc.item_description || "";
        let size = "";
        let numericalValue = null;
        let shape = "";
        let lotId = "";

       const match = description.match(/\/\s*([\d.]+)\s*CT/);
        if (match && match[1]) {
            numericalValue = parseFloat(match[1]);
        }

        const shapeMatch = description.match(/CT\s+([A-Z]+)\s*\//);
        if (shapeMatch && shapeMatch[1]) {
            shape = shapeMatch[1];
        }

        const lotIdMatch = description.match(/\/\s*(\d+)\s*$/);
        if (lotIdMatch && lotIdMatch[1]) {
            lotId = lotIdMatch[1];
        }

        frm.set_value("size", size);
        if (numericalValue !== null) {
            frm.set_value("size", numericalValue);
        }

        if (shape) {
            frm.set_value("shape", shape);
        }

        if (lotId) {
            frm.set_value("lot_id", lotId);
        }
        
    }, 
    fee: function(frm) {

        if(frm.doc.fee == 0){
            frm.set_value('ticker', 0)
        }
        else{
            frm.set_value('ticker', 1)
        }
    },
    vat: function(frm) {
        frm.set_value("pula", frm.doc.vat === 0 ? 0 : frm.doc.fee);
        frm.set_value("dollar", frm.doc.vat === 0 ? frm.doc.fee : 0);
        frm.set_value("con_dollar", frm.doc.dollar === 0 ? frm.doc.pula * 0.0726 : frm.doc.dollar);
    },
    service_description: function(frm) {
        let description = frm.doc.service_description || "";
        let type = "";

        // Convert to lowercase for case-insensitive matching
        description = description.toLowerCase();

        if (description.includes("recheck")) {
            type = "Check";
        } else if (description.includes("exam")) {
            type = "Exam";
        } else if (description.includes("final")) {
            type = "Final";
        } else {
            type = "Normal";
        }

        frm.set_value("type", type);
    }, 
    type: function(frm) {
        frm.set_value("type_2", frm.doc.type === "Normal" ? "Org" : "Re Chk");
    }, 
    size: function(frm) {
        let size = frm.doc.size;
        let size_group = ""
        if (size > 0 && size <= 0.29) {
            size_group = "30 DN";
        }
        else if (size >= 0.3 && size <= 0.499) {
            size_group = "30 TO 50 POINTER";
        }
        else if (size >= 0.5 && size <= 0.699) {
            size_group = "50 TO 70 POINTER";
        }
        else if (size >= 0.7 && size <= 0.899) {
            size_group = "70 TO 89 POINTER";
        }
        else if (size >= 0.9 && size <= 0.999) {
            size_group = "90 TO 99 POINTER";
        }
        else if (size >= 1.0 && size <= 1.99) {
            size_group = "1 CT TO 2 CTS";
        }
        else if (size >= 2.0 && size <= 4.99) {
            size_group = "2 CT TO 5 CTS";
        }
        else if (size >= 5 && size <= 49.99) {
            size_group = "5 CTS & UP";
        }
        frm.set_value("size_group", size_group);

    }
});