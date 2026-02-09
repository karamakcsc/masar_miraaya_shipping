// Copyright (c) 2026, KCSC and contributors
// For license information, please see license.txt

frappe.query_reports["Order Delivery Summary"] = {
	"filters": [
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
