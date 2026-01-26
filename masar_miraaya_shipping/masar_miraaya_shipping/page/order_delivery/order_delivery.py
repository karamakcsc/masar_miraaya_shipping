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
                "custom_magento_status": "On the Way"
            },
            [
                "name",
                "custom_magento_id",
                "customer_name",
                "custom_magento_status",
                "grand_total",
                "contact_phone",
                "address_display",
                "custom_delivery_company",
                "custom_driver_name",
                "custom_magento_billing_address"
            ],
            as_dict=True
        )

        if not so:
            continue

        data.append({
            "sales_order": so.name,
            "magento_id": so.custom_magento_id,
            "customer": so.customer_name,
            "grand_total": so.grand_total,
            "contact_phone": so.contact_phone,
            "address_display": so.custom_magento_billing_address if so.custom_magento_billing_address else so.address_display,
            "delivery_company": frappe.db.get_value("Customer", {"name": so.custom_delivery_company}, "customer_name") if so.custom_delivery_company else "-",
            "driver": so.custom_driver_name
        })

    return data


@frappe.whitelist()
def assign_driver_and_dispatch(sales_orders):
    sales_orders = frappe.parse_json(sales_orders)

    if not sales_orders:
        frappe.throw("No Sales Orders provided")

    for so_name in sales_orders:
        so = frappe.get_doc("Sales Order", so_name)
        
        if so.custom_magento_status != "On the Way":
            frappe.throw(f"{so.name} is no longer On the Way")
            
        so.custom_magento_status = "Delivered"
        so.save(ignore_permissions=True)

    return {
        "status": "success",
        "count": len(sales_orders)
    }
