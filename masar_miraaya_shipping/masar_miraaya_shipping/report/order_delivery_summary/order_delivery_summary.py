# Copyright (c) 2026, KCSC and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def get_data(filters):
	conditions = " tso.docstatus = 1 "

	_from, to = filters.get("from_date"), filters.get("to_date")
	if _from and to:
		conditions += f" AND tso.delivery_date BETWEEN '{_from}' AND '{to}'"

	return frappe.db.sql(f"""
		SELECT 
			tso.custom_magento_id,
			tso.delivery_date,
			tso.customer_name,
			tso.custom_magento_status,
			CASE 
				WHEN tso.custom_cash_on_delivery_amount = 0 THEN 'PrePaid'
				ELSE tso.custom_cash_on_delivery_amount
			END AS cod_amount,
			IFNULL(ret.return_qty, 0) AS return_qty,
			IFNULL(ret.return_amount, 0) AS return_amount
		FROM `tabSales Order` tso
		LEFT JOIN (
			SELECT 
				parent,
				SUM(qty) AS total_qty
			FROM `tabSales Order Item`
			GROUP BY parent
		) soi ON soi.parent = tso.name
		LEFT JOIN (
			SELECT
				dni.against_sales_order AS sales_order,
				ABS(SUM(dni.qty)) AS return_qty,
				ABS(SUM(dni.amount)) AS return_amount
			FROM `tabDelivery Note` dn
			INNER JOIN `tabDelivery Note Item` dni
				ON dni.parent = dn.name
			WHERE dn.is_return = 1
			  AND dn.docstatus = 1
			  AND dni.against_sales_order IS NOT NULL
			GROUP BY dni.against_sales_order
		) ret ON ret.sales_order = tso.name
		WHERE {conditions} AND tso.custom_magento_status IN ('On the Way', 'Delivered', 'Cancelled')
		ORDER BY tso.delivery_date DESC
	""", as_dict=True)

  
def get_columns():
    return [
		{"label": "Magento ID", "fieldname": "custom_magento_id", "fieldtype": "Data", "width": 175},
		{"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "Date", "width": 160},
		{"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
		{"label": "Magento Status", "fieldname": "custom_magento_status", "fieldtype": "Data", "width": 175},
		{"label": "COD Amount", "fieldname": "cod_amount", "fieldtype": "Currency", "width": 160},
		{"label": "Returned Qty", "fieldname": "return_qty", "fieldtype": "Float", "width": 160},
		{"label": "Returned Amount", "fieldname": "return_amount", "fieldtype": "Currency", "width": 160},
	]