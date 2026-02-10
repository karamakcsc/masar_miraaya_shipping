import frappe

@frappe.whitelist()
def scan_and_dispatch(sales_order, driver=None):
	so_name = sales_order

	so = frappe.db.get_value(
		"Sales Order",
		so_name,
		["name", "custom_magento_status", "delivery_date"],
		as_dict=True
	)

	if not so:
		return {
			"status": "error",
			"reason": "invalid_sales_order"
		}

	if so.custom_magento_status == "On the Way":
		return {
			"status": "error",
			"reason": "already_dispatched"
		}

	if so.custom_magento_status != "Fullfilled":
		return {
			"status": "error",
			"reason": "not_fulfilled"
		}

	pick_list = frappe.db.sql("""
		SELECT
			tpl.name,
			tpl.custom_driver,
			tpl.custom_driver_name,
			tpl.custom_delivery_company,
			tpl.custom_delivery_company_name
		FROM `tabPick List Item` tpli
		INNER JOIN `tabPick List` tpl
			ON tpl.name = tpli.parent
		WHERE
			tpli.sales_order = %s
			AND tpl.docstatus = 1
		ORDER BY tpl.modified DESC
		LIMIT 1
	""", so_name, as_dict=True)

	if not pick_list:
		return {
			"status": "error",
			"reason": "no_pick_list"
		}

	pick_list = pick_list[0]

	if driver and pick_list.custom_driver != driver:
		return {
			"status": "error",
			"reason": "driver_mismatch"
		}

	if not pick_list.custom_driver or not pick_list.custom_delivery_company:
		return {
			"status": "error",
			"reason": "driver_not_assigned"
		}

	so_doc = frappe.get_doc("Sales Order", so_name)
	so_doc.custom_driver = pick_list.custom_driver
	so_doc.custom_delivery_company = pick_list.custom_delivery_company
	so_doc.custom_magento_status = "On the Way"
	so_doc.save(ignore_permissions=True)

	data = frappe.db.sql("""
		SELECT
			so.name AS sales_order,
			so.custom_magento_id AS magento_id,
            so.custom_magento_status AS magento_status,
			so.customer_name AS customer,
			so.grand_total,
			so.contact_phone,
			COALESCE(
				so.custom_magento_billing_address,
				so.address_display
			) AS address_display,
			so.custom_driver_name AS driver
		FROM `tabSales Order` so
		WHERE so.name = %s
	""", so_name, as_dict=True)

	return {
		"status": "success",
		"data": data[0] if data else {}
	}

@frappe.whitelist()
def get_dispatched_orders(driver=None, from_date=None, to_date=None):
    if not driver:
        return []
    
    conditions = ["custom_magento_status = 'On the Way'"]

    if driver:
        conditions.append(f"custom_driver = '{driver}'")
    if from_date:
        conditions.append(f"delivery_date >= '{from_date}'")
    if to_date:
        conditions.append(f"delivery_date <= '{to_date}'")

    where_clause = " AND ".join(conditions)

    orders = frappe.db.sql(f"""
        SELECT
            name AS sales_order,
            custom_magento_id AS magento_id,
            custom_magento_status AS magento_status,
            customer_name AS customer,
            grand_total,
            contact_phone,
            COALESCE(custom_magento_billing_address, address_display) AS address_display,
            custom_driver_name AS driver
        FROM `tabSales Order`
        WHERE {where_clause}
        ORDER BY modified DESC
    """, as_dict=True)

    return orders