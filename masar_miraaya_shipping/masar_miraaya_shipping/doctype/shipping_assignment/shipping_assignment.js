// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shipping Assignment", {
	refresh: function(frm) {
        fetch_orders(frm);
	},
    delivery_company: function(frm) {
        if (frm.doc.delivery_company) {
            frm.doc.orders.forEach(function(order) {
                order.delivery_company = frm.doc.delivery_company;
                order.delivery_company_name = frm.doc.delivery_company_name;
            })
            frm.refresh_field("orders");
        }
    },
    driver: function(frm) {
        if (frm.doc.driver) {
            frm.doc.orders.forEach(function(order) {
                order.driver = frm.doc.driver;
                order.driver_name = frm.doc.driver_name;
            })
            frm.refresh_field("orders");
        }
    }
});


function fetch_orders(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.__islocal != 1) {
        frm.add_custom_button(__("Fetch Orders"), function() {
            frappe.call({
                doc: frm.doc,
                method: "fetch_orders",
                args: {
                    delivery_date: frm.doc.delivery_date,
                    delivery_time: frm.doc.delivery_time,
                    expected_delivery_company: frm.doc.expected_delivery_company,
                    governorate: frm.doc.governorate,
                    delivery_zone: frm.doc.delivery_zone,
                    magento_id: frm.doc.magento_id
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frm.clear_table("orders");
                        r.message.forEach(function(order) {
                            let row = frm.add_child("orders");
                            row.sales_order = order.name;
                            row.magento_id = order.custom_magento_id;
                            row.customer = order.customer;
                            row.customer_name = order.customer_name;
                            row.grand_total = order.grand_total;
                            row.delivery_zone = order.custom_delivery_zone || frm.doc.delivery_zone;
                            row.driver = frm.doc.driver || row.driver;
                            row.driver_name = frm.doc.driver_name || row.driver_name 
                            row.delivery_company = frm.doc.delivery_company || row.delivery_company;
                            row.delivery_company_name = frm.doc.delivery_company_name || row.delivery_company_name;
                        });
                        frm.refresh_field("orders");
                    } else {
                        frappe.msgprint(__("No orders found matching the criteria."));
                    }
                }
            });
        });
    }
}