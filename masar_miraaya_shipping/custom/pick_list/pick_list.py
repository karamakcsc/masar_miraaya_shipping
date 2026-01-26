import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds, format_duration


def validate(self, method):
    if not self.custom_picking_datetime and self.docstatus == 0:
        self.custom_picking_datetime = now_datetime()
def on_submit(self, method):
    validate_picked_qty(self)       
    stop_picking_timer(self)

def validate_picked_qty(self):
    for item in self.locations:
        if item.picked_qty <= 0:
            frappe.throw(_(f"Picked Quantity must be greater than zero for item {item.item_code} in row {item.idx}"))
    if not self.custom_assigned:
        frappe.throw(_("Please assign the picker before submitting the Pick List."))


@frappe.whitelist()
def start_picking_timer(pick_list_name):
    doc = frappe.get_doc("Pick List", pick_list_name)
    
    if not doc.custom_picking_datetime:
        doc.custom_picking_datetime = now_datetime()
        if not doc.custom_picking_user:
            doc.custom_picking_user = frappe.session.user
        doc.save(ignore_permissions=True)
        
    return {
        "success": True,
        "start_time": doc.custom_picking_datetime
    }
    
@frappe.whitelist()
def start_packing_timer(pick_list_name):
    doc = frappe.get_doc("Pick List", pick_list_name)
    
    if not doc.custom_packing_datetime:
        doc.custom_packing_datetime = now_datetime()
        if not doc.custom_packing_user:
            doc.custom_packing_user = frappe.session.user
        doc.save(ignore_permissions=True)
        
    return {
        "success": True,
        "start_time": doc.custom_packing_datetime
    }
    
def stop_picking_timer(self):
    if self.custom_picking_datetime and not self.custom_picking_end_datetime:
        self.custom_picking_end_datetime = now_datetime()
        self.custom_picking_duration = time_diff_in_seconds(self.custom_picking_end_datetime, self.custom_picking_datetime)
        if not self.custom_picking_user:
            self.custom_picking_user = frappe.session.user
        self.save(ignore_permissions=True)