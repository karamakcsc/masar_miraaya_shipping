// Copyright (c) 2026, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shipping Label Print", {
    refresh: function(frm) {
        hide_buttons(frm);
        print_labels(frm);
        fetch_orders(frm);
    },
    onload: function(frm) {
        hide_buttons(frm);
    },
    delivery_method: function(frm) {
        if (frm.doc.delivery_method) {
            frm.doc.delivery_company = null;
            frm.doc.delivery_company_name = null;
            frm.doc.orders.forEach(function(order) {
                order.delivery_method = frm.doc.delivery_method;
            });
            frm.refresh_field("orders");
        }
    },
    delivery_company: function(frm) {
        if (frm.doc.delivery_company) {
            frm.doc.orders.forEach(function(order) {
                order.delivery_company = frm.doc.delivery_company;
                order.delivery_company_name = frm.doc.delivery_company_name;
            });
            frm.refresh_field("orders");
        }
    }
});


function print_labels(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.orders?.length) {

        frm.add_custom_button(__('Print Labels'), function () {

            const total_rows = frm.doc.orders.length;

            const dialog = new frappe.ui.Dialog({
                title: __('Print Labels Range'),
                fields: [
                    {
                        fieldtype: 'Int',
                        fieldname: 'total_orders',
                        label: __('Total Orders'),
                        read_only: 1,
                        default: total_rows
                    },
                    {
                        fieldtype: 'Int',
                        fieldname: 'from_idx',
                        label: __('From Row'),
                        reqd: 1,
                        default: 1
                    },
                    {
                        fieldtype: 'Int',
                        fieldname: 'to_idx',
                        label: __('To Row'),
                        reqd: 1,
                        default: total_rows
                    }
                ],
                primary_action_label: __('Print'),
                primary_action(values) {

                    if (values.from_idx < 1 || values.to_idx > total_rows) {
                        frappe.msgprint(
                            __('Row range must be between 1 and {0}', [total_rows])
                        );
                        return;
                    }

                    if (values.from_idx > values.to_idx) {
                        frappe.msgprint(__('From Row cannot be greater than To Row'));
                        return;
                    }

                    frappe.call({
                        doc: frm.doc,
                        method: "mark_as_printed",
                        freeze: true,
                        callback: function (r) {
                            if (!r.exc) {

                                const base_url = window.location.origin;
                                const print_format = "Shipping Label Print";

                                const url =
                                    `${base_url}/printview` +
                                    `?doctype=${encodeURIComponent(frm.doc.doctype)}` +
                                    `&name=${encodeURIComponent(frm.doc.name)}` +
                                    `&format=${encodeURIComponent(print_format)}` +
                                    `&no_letterhead=1` +
                                    `&from_idx=${values.from_idx}` +
                                    `&to_idx=${values.to_idx}`;

                                window.open(url, "_blank");
                                frm.reload_doc();
                                dialog.hide();
                            }
                        }
                    });
                }
            });

            dialog.show();
        });
    }
}


function hide_buttons(frm) {
    $('button[data-original-title="Print"].btn.btn-default.icon-btn').hide();
}

function fetch_orders(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.__islocal != 1) {
        frm.add_custom_button(__("Fetch Orders"), function() {
            frappe.call({
                method: "masar_miraaya_shipping.masar_miraaya_shipping.doctype.shipping_label_print.shipping_label_print.get_filtered_orders",
                args: {
                    delivery_date: frm.doc.delivery_date,
                    delivery_time: frm.doc.delivery_time,
                    governorate: frm.doc.governorate || [],
                    order_status: frm.doc.order_status
                },
                callback: function(r) {
                    if (r.message && r.message.orders && r.message.orders.length > 0) {
                        frm.clear_table("orders");
                        
                        r.message.orders.forEach(function(order) {
                            let row = frm.add_child("orders");
                            row.sales_order = order.name;
                            row.customer_name = order.customer_name;
                            row.address = order.address;
                            row.city = order.city;
                            row.landmark = order.landmark;
                            row.contact_no = order.mobile_no;
                            row.delivery_date = order.delivery_date;
                            row.delivery_time = order.custom_delivery_time;
                            row.total_qty = order.total_qty;
                            row.grand_total = order.grand_total;
                            row.magento_id = order.custom_magento_id;
                            row.governorate = order.custom_governorate;
                            row.district = order.custom_district;
                            row.delivery_zone = order.delivery_zone;
                            row.delivery_method = order.delivery_method || frm.doc.delivery_method;
                            row.delivery_company = order.delivery_company || frm.doc.delivery_company;
                            row.delivery_company_name = order.delivery_company_name || frm.doc.delivery_company_name;
                            row.payment_method = order.payment_method;
                        });
                        
                        frm.refresh_field("orders");
                        
                        if (r.message.grouped_orders) {
                            show_grouping_message(frm, r.message.grouped_orders, r.message.zones);
                        }
                    } else {
                        frappe.msgprint(__("No orders found for the selected criteria."));
                    }
                }
            });
        });
    }
}

function show_grouping_message(frm, grouped_orders, zones) {
    let message = `<div style="margin: 10px 0;">
        <strong>Orders grouped by Delivery Zone:</strong><br>`;
    
    zones.forEach(function(zone) {
        const count = grouped_orders[zone].length;
        message += `<div style="margin: 5px 0;">
            <strong>${zone}:</strong> ${count} order(s)
        </div>`;
    });
    
    message += `</div>`;
    
    frappe.msgprint({
        title: __('Order Grouping Summary'),
        message: message,
        indicator: 'green'
    });
}