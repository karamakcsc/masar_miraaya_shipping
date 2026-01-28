# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ShippingAssignment(Document):
	@frappe.whitelist()
	def fetch_orders(
     self, delivery_date=None, delivery_time=None, expected_delivery_company=None, 
     governorate=None, delivery_zone=None, magento_id=None
     ):
		conditions = " 1=1 "

		if delivery_date:
			conditions += f" AND tso.delivery_date = '{delivery_date}' "
		if delivery_time:
			conditions += f" AND tso.custom_delivery_time = '{delivery_time}' "
		if expected_delivery_company:
			conditions += f" AND tso.custom_expected_delivery_company = '{expected_delivery_company}' "
		if governorate:
			conditions += f" AND tpl.custom_governorate = '{governorate}' "
		if delivery_zone:
			conditions += f" AND tpl.custom_delivery_zone = '{delivery_zone}' "
		if magento_id:
			conditions += f" AND tso.custom_magento_id LIKE '%{magento_id}%' "

		orders_sql = frappe.db.sql(f"""
            SELECT 
            	tso.name, 
             	tso.custom_magento_id, 
              	tso.customer, 
               	tso.customer_name, 
                tso.grand_total, 
                tpl.custom_delivery_zone
			FROM `tabSales Order` tso 
			LEFT JOIN `tabPick List Item` tpli ON tso.name = tpli.sales_order
			LEFT JOIN `tabPick List` tpl ON tpl.name = tpli.parent
			WHERE
				{conditions}
				AND tso.docstatus = 1
				AND tso.custom_magento_status = "Fullfilled"
				AND tso.custom_manually = 0
			GROUP BY tso.name
		""", as_dict=True)

		return orders_sql

	def on_submit(self):
		self.set_data_to_pl()


	def set_data_to_pl(self):
		if self.orders:
			for order in self.orders:
				pl = get_linked_pl(order.sales_order)
				if pl:
					if not self.delivery_company or not self.driver:
						frappe.throw("Driver and Delivery Company are mandatory")

					pl_doc = frappe.get_doc("Pick List", pl)
					old_delivery_company = pl_doc.get("custom_delivery_company")
					old_delivery_company_name = pl_doc.get("custom_delivery_company_name")
					old_driver = pl_doc.get("custom_driver")
					old_driver_name = pl_doc.get("custom_driver_name")
					
					frappe.db.set_value(pl_doc.doctype, pl_doc.name, "custom_delivery_company", self.delivery_company)
					frappe.db.set_value(pl_doc.doctype, pl_doc.name, "custom_delivery_company_name", self.delivery_company_name)
					frappe.db.set_value(pl_doc.doctype, pl_doc.name, "custom_driver", self.driver)
					frappe.db.set_value(pl_doc.doctype, pl_doc.name, "custom_driver_name", self.driver_name)
					
					if old_delivery_company != self.delivery_company:
						create_version_log(pl_doc.doctype, pl_doc.name, "custom_delivery_company", old_delivery_company, self.delivery_company)
					if old_delivery_company_name != self.delivery_company_name:
						create_version_log(pl_doc.doctype, pl_doc.name, "custom_delivery_company_name", old_delivery_company_name, self.delivery_company_name)
					if old_driver != self.driver:
						create_version_log(pl_doc.doctype, pl_doc.name, "custom_driver", old_driver, self.driver)
					if old_driver_name != self.driver_name:
						create_version_log(pl_doc.doctype, pl_doc.name, "custom_driver_name", old_driver_name, self.driver_name)
					order.pick_list = pl
			frappe.db.commit()
			

def create_version_log(doctype, docname, field, old_value, new_value):
    version = frappe.new_doc("Version")
    version.ref_doctype = doctype
    version.docname = docname
    version.data = frappe.as_json({
        "changed": [
            [field, old_value, new_value]
        ]
    })
    version.save(ignore_permissions=True)

def get_linked_pl(so):
    if not so:
        return None
    
    pl_sql = frappe.db.sql("""
        SELECT DISTINCT
			tpl.name
		FROM `tabPick List` tpl
		INNER JOIN `tabPick List Item` tpli ON tpl.name = tpli.parent
		WHERE tpli.sales_order = %s
	""", (so,), as_dict=True)
    
    if pl_sql and pl_sql[0] and pl_sql[0]["name"]:
        return pl_sql[0]["name"]
    return None