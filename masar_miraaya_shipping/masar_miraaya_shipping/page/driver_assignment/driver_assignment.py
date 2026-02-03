import frappe

@frappe.whitelist()
def get_so_dispatch_details(sales_orders):
    sales_orders = frappe.parse_json(sales_orders)

    data = []

    for so_name in sales_orders:
        so = frappe.db.get_value(
            "Sales Order",
            {
                "name": so_name,
                "custom_magento_status": "Fullfilled"
            },
            [
                "name",
                "custom_magento_id",
                "customer_name",
                "custom_magento_status",
                "grand_total",
                "contact_phone",
                "address_display",
                "custom_magento_billing_address"
            ],
            as_dict=True
        )

        if not so:
            continue

        pick_list = frappe.db.sql("""
            SELECT 
                tpl.custom_driver_name,
                tpl.custom_delivery_company_name
            FROM `tabPick List Item` tpli
            INNER JOIN `tabPick List` tpl ON tpl.name = tpli.parent
            WHERE 
                tpli.sales_order = %s
                AND tpl.docstatus = 1
            ORDER BY tpl.modified DESC
            LIMIT 1
        """, (so.name,), as_dict=True)

        data.append({
            "sales_order": so.name,
            "magento_id": so.custom_magento_id,
            "customer": so.customer_name,
            "grand_total": so.grand_total,
            "contact_phone": so.contact_phone,
            "address_display": so.custom_magento_billing_address if so.custom_magento_billing_address else so.address_display,
            "delivery_company": pick_list[0].custom_delivery_company_name if pick_list else "-",
            "driver": pick_list[0].custom_driver_name if pick_list else "-"
        })

    return data


@frappe.whitelist()
def assign_driver_and_dispatch(sales_orders):
    sales_orders = frappe.parse_json(sales_orders)

    if not sales_orders:
        frappe.throw("No Sales Orders provided")

    for so_name in sales_orders:
        so = frappe.get_doc("Sales Order", so_name)
        
        if so.custom_magento_status != "Fullfilled":
            frappe.throw(f"{so.name} is no longer Fullfilled")

        pick_list = frappe.db.sql("""
            SELECT tpl.name, tpl.custom_driver, tpl.custom_delivery_company
            FROM `tabPick List Item` tpli
            INNER JOIN `tabPick List` tpl ON tpl.name = tpli.parent
            WHERE tpli.sales_order = %s AND tpl.docstatus = 1
            ORDER BY tpl.modified DESC
            LIMIT 1
        """, (so_name,), as_dict=True)

        if not pick_list:
            frappe.throw(f"No submitted Pick List found for {so.name}")
            
        pick_list = pick_list[0]
        
        if not pick_list.custom_driver or not pick_list.custom_delivery_company:
            frappe.throw(f"Driver or Delivery Company are not assigned.")

        so.custom_driver = pick_list.custom_driver
        so.custom_delivery_company = pick_list.custom_delivery_company
        so.custom_magento_status = "On the Way"
        so.save(ignore_permissions=True)

    return {
        "status": "success",
        "count": len(sales_orders)
    }
