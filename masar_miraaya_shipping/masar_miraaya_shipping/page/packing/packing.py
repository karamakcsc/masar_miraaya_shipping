import frappe


@frappe.whitelist()
def get_picklist_from_so(so):
    if not so:
        return {
            "success": False,
            "message": "No Pick List, Sales Order, or Magento ID provided"
        }

    if frappe.db.exists("Pick List", so):
        if frappe.db.exists("Pick List", {
            "name": so,
            "docstatus": 1
        }):
            return {
                "success": True,
                "pick_list": so
            }

    so_sql = frappe.db.sql("""
        SELECT DISTINCT tpli.parent AS pick_list
        FROM `tabPick List Item` tpli
        INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
        INNER JOIN `tabPick List` tpl ON tpli.parent = tpl.name
        WHERE tso.name = %s
          AND tso.custom_magento_status = 'Picked'
          AND tpl.docstatus = 1
    """, (so,), as_dict=True)

    if so_sql:
        return {
            "success": True,
            "pick_list": so_sql[0].pick_list
        }

    magento_sql = frappe.db.sql("""
        SELECT DISTINCT tpl.name AS pick_list
        FROM `tabPick List` tpl
        INNER JOIN `tabPick List Item` tpli ON tpl.name = tpli.parent
        INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
        WHERE tpl.custom_magento_id = %s
          AND tso.custom_magento_status = 'Picked'
          AND tpl.docstatus = 1
    """, (so,), as_dict=True)

    if magento_sql:
        return {
            "success": True,
            "pick_list": magento_sql[0].pick_list
        }

    return {
        "success": False,
        "message": "Packing is not allowed. Sales Order status must be 'Picked'."
    }

@frappe.whitelist()
def get_confirmed_sales_orders(so):
    if not so:
        return None
    
    if frappe.db.exists("Pick List", so):
        picklist_sql = frappe.db.sql("""
            SELECT DISTINCT
                tso.name, 
                tso.custom_magento_id, 
                tso.customer_name, 
                tso.transaction_date, 
                tso.total_qty, 
                tso.grand_total
            FROM `tabPick List` tpl
            INNER JOIN `tabPick List Item` tpli ON tpl.name = tpli.parent
            INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
            WHERE tpl.name = %s AND tso.custom_magento_status = 'Picked'
        """, (so,), as_dict=True)
        
        if picklist_sql:
            return picklist_sql
        
    so_sql = frappe.db.sql("""
        SELECT DISTINCT 
            tso.name, 
            tso.custom_magento_id, 
            tso.customer_name, 
            tso.transaction_date, 
            tso.total_qty, 
            tso.grand_total
        FROM `tabSales Order` tso
        WHERE tso.name = %s AND tso.custom_magento_status = 'Picked'
    """,(so,), as_dict=True)
    
    if so_sql:
        return so_sql
    
    magneto_id_sql = frappe.db.sql("""
        SELECT DISTINCT
            tso.name, 
            tso.custom_magento_id, 
            tso.customer_name, 
            tso.transaction_date, 
            tso.total_qty, 
            tso.grand_total
        FROM `tabSales Order` tso
        WHERE tso.custom_magento_id = %s AND tso.custom_magento_status = 'Picked'
    """, (so,), as_dict=True)
    
    if magneto_id_sql:
        return magneto_id_sql
    return None