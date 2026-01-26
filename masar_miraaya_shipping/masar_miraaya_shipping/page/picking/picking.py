import frappe


@frappe.whitelist()
def get_picklist_from_so(so):
    if not so:
        return {
            "succsses": False,
            "message": "No Pick List or Sales Order or Magento ID"
        }
    
    if frappe.db.exists("Pick List", so):
        picklist_sql = frappe.db.sql("""
                SELECT DISTINCT tpli.parent AS pick_list
                FROM `tabPick List Item` tpli
                INNER JOIN `tabPick List` tpl ON tpli.parent = tpl.name
                INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
                WHERE tpl.name = %s AND tso.custom_magento_status = 'Confirmed' AND tpl.docstatus = 0
            """,(so,), as_dict=True)
        if picklist_sql:
            return so
    
    so_sql = frappe.db.sql("""
        SELECT DISTINCT tpli.parent AS pick_list
        FROM `tabPick List Item` tpli
        INNER JOIN `tabPick List` tpl ON tpli.parent = tpl.name
        INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
        WHERE tso.name = %s AND tso.custom_magento_status = 'Confirmed' AND tpl.docstatus = 0
    """,(so,), as_dict=True)
    
    if so_sql:
        return so_sql[0].pick_list
    
    magneto_id_sql = frappe.db.sql("""
        SELECT DISTINCT tpl.name AS pick_list
        FROM `tabPick List` tpl
        INNER JOIN `tabPick List Item` tpli ON tpl.name = tpli.parent
        INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
        WHERE tpl.custom_magento_id = %s AND tso.custom_magento_status = 'Confirmed' AND tpl.docstatus = 0
    """, (so,), as_dict=True)
    
    if magneto_id_sql:
        return magneto_id_sql[0].pick_list
    return {
            "succsses": False,
            "message": "The picking process is not valid right now the Sales Order Status must be 'Confirmed' and the Pick List must be draft"
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
            WHERE tpl.name = %s AND tso.custom_magento_status = 'Confirmed'
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
        WHERE tso.name = %s AND tso.custom_magento_status = 'Confirmed'
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
        WHERE tso.custom_magento_id = %s AND tso.custom_magento_status = 'Confirmed'
    """, (so,), as_dict=True)
    
    if magneto_id_sql:
        return magneto_id_sql
    return None