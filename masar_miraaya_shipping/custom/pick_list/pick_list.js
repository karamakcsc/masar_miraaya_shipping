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

frappe.ui.form.on('Pick List', {

    refresh(frm) {
        if (frm.fields_dict.custom_scan_packaging_barcode) {
            frm.fields_dict.custom_scan_packaging_barcode.$input.on("keypress", function(e) {
                if (e.which === 13) {
                    frm.trigger("custom_scan_packaging_barcode");
                }
            });
        }
    },

    custom_scan_packaging_barcode(frm) {

        if (!frm.doc.custom_scan_packaging_barcode) return;

        let barcode = frm.doc.custom_scan_packaging_barcode;

        frappe.db.get_value("Item", { name: barcode }, ["name", "item_name"])
            .then(r => {

                if (r.message) {
                    process_item(frm, r.message.name, r.message.item_name);
                    return;
                }

                frappe.db.get_value("Item Barcode", { barcode: barcode }, "parent")
                    .then(res => {

                        if (!res.message) {
                            frappe.msgprint("Barcode not found");
                            frm.set_value("custom_scan_packaging_barcode", "");
                            return;
                        }

                        let item_code = res.message.parent;

                        frappe.db.get_value("Item", item_code, ["name", "item_name"])
                            .then(item => {
                                process_item(frm, item.message.name, item.message.item_name);
                            });
                    });
            });
    }
});


function process_item(frm, item_code, item_name) {

    let existing = frm.doc.custom_packaging_items.find(d => d.item_code === item_code);

    if (existing) {
        frappe.show_alert({
            message: `${item_name} already added`,
            indicator: "orange"
        });
    } else {

        let child = frm.add_child("custom_packaging_items");

        child.item_code = item_code;
        child.item_name = item_name;

        frm.refresh_field("custom_packaging_items");

        frappe.show_alert({
            message: `${item_name} added`,
            indicator: "green"
        });
    }

    frm.set_value("custom_scan_packaging_barcode", "");
}