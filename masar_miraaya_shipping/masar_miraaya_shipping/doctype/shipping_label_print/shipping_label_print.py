import frappe
from frappe.model.document import Document
import barcode
from barcode.writer import ImageWriter
import io
import base64
from masar_miraaya.api import base_data, request_with_history


class ShippingLabelPrint(Document):
    def validate(self):
        self.total_orders = len(self.orders)
        for order in self.orders:
            picklist_no = self.get_picklist(order.sales_order)
            dn_no = self.get_delivery_note(order.sales_order)
            if picklist_no:
                order.pick_list = picklist_no
            if dn_no:
                order.delivery_note = dn_no
    
    def on_submit(self):
        if not self.orders:
            frappe.throw("Please add at least one order to print shipping label.")
        if not self.printed_by:
            self.printed_by = frappe.session.user
        self.generate_barcodes()
        self.print_status = "Printed"
        self.set_shipping_details_pl()
    
    def on_cancel(self):
        self.print_status = "Cancelled"
        for order in self.orders:
            order.qr_active = 0
            
    def get_picklist(self, sales_order):
        existing_pl = frappe.db.sql("""
            SELECT DISTINCT tpli.parent AS pick_list
            FROM `tabPick List Item` tpli
            INNER JOIN `tabSales Order` tso ON tpli.sales_order = tso.name
            INNER JOIN `tabPick List` tpl ON tpli.parent = tpl.name
            WHERE tso.name = %s
            GROUP BY tpli.parent
        """,(sales_order,), as_dict=True)
        
        if existing_pl:
            return existing_pl[0].pick_list
        else:
            frappe.throw(f"Pick List not found for Sales Order {sales_order}.")
        return None

    def get_delivery_note(self, sales_order):
        existing_dn = frappe.db.sql("""
            SELECT DISTINCT tdn.name 
            FROM `tabDelivery Note` tdn 
            INNER JOIN `tabDelivery Note Item` tdni ON tdn.name = tdni.parent 
            WHERE tdni.against_sales_order = %s
            GROUP BY tdn.name
        """, sales_order, as_dict=True)
        
        if existing_dn:
            return existing_dn[0].name
        return None
    
    def set_shipping_details_pl(self):
        for order in self.orders:
            if order.pick_list:
                pl_doc = frappe.get_doc("Pick List", order.pick_list)
                pl_doc.custom_delivery_zone = order.delivery_zone if order.delivery_zone else ""                
                
                pl_doc.save(ignore_permissions=True)

    def generate_barcodes(self):
        for order in self.orders:
            if order.pick_list:
                    pl_barcode = self.create_barcode(order.pick_list)
                    order.picklist_barcode = pl_barcode
            if order.delivery_method and order.delivery_method == "In-House":
                so_barcode = self.create_barcode(order.sales_order)
                order.order_barcode = so_barcode
            elif order.delivery_method and order.delivery_method == "Outsourced":
                if not order.delivery_company or not order.delivery_company_name:
                    frappe.throw(f"Please set Delivery Company for Sales Order {order.sales_order} before printing the label.")
                expected_delivery_company = frappe.db.get_value("Sales Order", order.sales_order, "custom_expected_delivery_company")
                base_url, headers = base_data("magento")
                if order.delivery_company_name == expected_delivery_company:
                    get_url = f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/label/{order.magento_id}"
                    response = request_with_history(
                        req_method='GET', 
                        document=self.doctype, 
                        doctype=self.name, 
                        url=get_url, 
                        headers=headers
                    )
                    if response.status_code == 200:
                        response_json = response.json()
                        if response_json:
                            order.outsourced_label = f"data:image/png;base64,{response_json['label_base64']}"
                        # if 'label_base64' in response_json:
                        #     order.outsourced_label = f"data:image/png;base64,{response_json['label_base64']}"
                        else:
                            frappe.throw(f"Label data not found in response for Sales Order {order.sales_order} Magento ID {order.magento_id}.")
                elif order.delivery_company_name and order.expected_delivery_company and order.delivery_company_name != expected_delivery_company:
                    post_url = f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/reassign"
                    
                    payload = {
                        "incrementId": order.magento_id,
                        "shippingMethod": order.delivery_company_name
                    }
                    
                    response = request_with_history(
                        req_method='POST', 
                        document=self.doctype, 
                        doctype=self.name, 
                        url=post_url, 
                        headers=headers, 
                        data=payload
                    )
                    if response.status_code == 200:
                        get_url = f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/label/{order.magento_id}"
                        response = request_with_history(
                            req_method='GET', 
                            document=self.doctype, 
                            doctype=self.name, 
                            url=get_url, 
                            headers=headers
                        )
                        if response.status_code == 200:
                            response_json = response.json()
                            if response_json:
                                order.outsourced_label = f"data:image/png;base64,{response_json}"
                            else:
                                frappe.throw(f"Label data not found in response for Sales Order {order.sales_order} Magento ID {order.magento_id}.")
                    else:
                        frappe.throw(f"Failed to reassign shipping method for Sales Order {order.sales_order} Magento ID {order.magento_id}. Response: {response.text}")
                    
                    
        self.save(ignore_permissions=True)
    
    def create_barcode(self, text):
        try:
            barcode_class = barcode.get_barcode_class('code128')
            
            barcode_instance = barcode_class(text, writer=ImageWriter())
            
            buffer = io.BytesIO()
            barcode_instance.write(buffer, options={
                'module_width': 0.2,
                'module_height': 15.0,
                'quiet_zone': 6.5,
                'font_size': 10,
                'text_distance': 5.0,
                'write_text': True
            })
            
            buffer.seek(0)
            barcode_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            return f"data:image/png;base64,{barcode_base64}"
        
        except Exception as e:
            frappe.log_error(f"Barcode generation failed for {text}: {str(e)}")
            return None
        
    @frappe.whitelist()
    def mark_as_printed(self):        
        for order in self.orders:
            order.label_printed = 1
            order.print_count = (order.print_count or 0) + 1
        
        if self.print_status == "Printed":
            self.print_status = "Reprinted"
        else:
            self.print_status = "Printed"
        
        self.save()
        return True
    
@frappe.whitelist()
def get_filtered_orders(delivery_date, delivery_time, governorate, order_status):
    filters = {
        "delivery_date": delivery_date,
        "custom_delivery_time": delivery_time,
        "custom_magento_status": order_status,
        "custom_governorate": governorate,
        "docstatus": 1,
        "custom_manually": 0,
    }
    
    orders = frappe.get_all(
        "Sales Order",
        filters=filters,
        fields=["name", "customer", "customer_name", "delivery_date", "custom_delivery_time", 
                "grand_total", "custom_governorate", "total_qty", "customer_address", 
                "custom_magento_id"
        ],
        order_by="custom_governorate, name"
    )
    
    for order in orders:
        order["address"] = ""
        order["city"] = ""
        order["landmark"] = ""
        order["mobile_no"] = ""
        if order.customer_address:
            address_doc = frappe.get_doc("Address", order.customer_address)
            order["address"] = address_doc.address_line1
            order["city"] = address_doc.city
            order["landmark"] = address_doc.address_title
            order["mobile_no"] = address_doc.phone
    
    return {
        'orders': orders,
    }