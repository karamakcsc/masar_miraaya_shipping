// Copyright (c) 2026, KCSC and contributors
// For license information, please see license.txt

frappe.query_reports["Order Delivery Summary"] = {
	"filters": [
		{
			"fieldname": "sales_order",
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"get_query": function() {
				return {
					"filters": {
						"docstatus": 1,
						"custom_manually": 0,
						"custom_magento_status": ["in", ["On the Way", "Delivered", "Cancelled"]]
					}
				};
			}
		},
		{
			"fieldname": "magento_id",
			"label": __("Magento ID"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"fieldname": "magento_status",
			"label": __("Magento Status"),
			"fieldtype": "Select",
			"options": "\nOn the Way\nDelivered\nCancelled",
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
		},
	]
};
