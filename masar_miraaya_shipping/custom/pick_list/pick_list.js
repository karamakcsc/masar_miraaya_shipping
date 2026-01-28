frappe.ui.form.on("Pick List", {
    onload: function(frm) {
        if (frm.doc.__islocal != 1 && frm.doc.docstatus === 0 && !frm.doc.custom_picking_end_datetime) {
            start_picking_timer(frm);
        }
        if (frm.doc.docstatus === 1 && !frm.doc.custom_packing_end_datetime) {
            start_packing_timer(frm);
        }
    }
});

function start_picking_timer(frm) {
    frappe.call({
        method: "masar_miraaya_shipping.custom.pick_list.pick_list.start_picking_timer",
        args: {
            pick_list_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.refresh_field("custom_picking_datetime");
                frm.refresh_field("custom_picking_user");
                frm.refresh_field("custom_picking_end_datetime");
            }
        }
    });
}

function start_packing_timer(frm) {
    frappe.call({
        method: "masar_miraaya_shipping.custom.pick_list.pick_list.start_packing_timer",
        args: {
            pick_list_name: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frm.refresh_field("custom_packing_datetime");
                frm.refresh_field("custom_packing_user");
                frm.refresh_field("custom_packing_end_datetime");
            }
        }
    });
}