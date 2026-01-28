// Copyright (c) 2026, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Delivery Zone", {
	refresh: function(frm) {
        set_multiselect_filter(frm);
	},
    governorate_ms: function(frm) {
        set_multiselect_filter(frm);
    }
});


function set_multiselect_filter(frm) {
    const governorates = (frm.doc.governorate_ms || []).map(
        row => row.governorate
    );

    frm.set_query('district_ms', function () {
        return {
            filters: [
                ['District', 'governorate', 'in', governorates]
            ]
        };
    });
}