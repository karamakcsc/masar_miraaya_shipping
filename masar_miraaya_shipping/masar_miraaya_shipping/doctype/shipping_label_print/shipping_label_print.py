import frappe
from frappe.model.document import Document
import barcode
from barcode.writer import ImageWriter
import io
import base64
from masar_miraaya.api import base_data, request_with_history
from frappe.utils import now_datetime
import json
from pdf2image import convert_from_bytes
import re


class ShippingLabelPrint(Document):
    def validate(self):
        self.total_orders = len(self.orders)
        for order in self.orders:
            self.set_location_details(order)           
            self.auto_assign_delivery_zone(order)
            
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
    
    def set_location_details(self, order):
        if order.sales_order:
            so_doc = frappe.get_doc("Sales Order", order.sales_order)
            
            if hasattr(so_doc, 'custom_governorate') and so_doc.custom_governorate:
                order.governorate = so_doc.custom_governorate
            
            if hasattr(so_doc, 'custom_district') and so_doc.custom_district:
                order.district = so_doc.custom_district
    
    def auto_assign_delivery_zone(self, order):
        if not order.governorate:
            frappe.throw(f"Governorate not found for Sales Order {order.sales_order}")

        dz = frappe.qb.DocType("Delivery Zone")
        dzg = frappe.qb.DocType("Governorate MultiSelect")
        dzd = frappe.qb.DocType("District MultiSelect")

        base_query = (
            frappe.qb.from_(dz)
            .join(dzg).on(
                (dzg.parent == dz.name) &
                (dzg.governorate == order.governorate)
            )
            .select(dz.name)
            .where(
                (dz.is_enabled == 1)
            )
        )

        if order.district:
            exact_zone = (
                base_query
                .join(dzd).on(
                    (dzd.parent == dz.name) &
                    (dzd.district == order.district)
                )
                .orderby(dz.creation, order=frappe.qb.desc)
                .limit(1)
                .run(as_dict=True)
            )

            if exact_zone:
                order.delivery_zone = exact_zone[0]["name"]
                return

        governorate_zones = (
            base_query
            .orderby(dz.creation, order=frappe.qb.desc)
            .run(as_dict=True)
        )

        if governorate_zones:
            catch_all = [z for z in governorate_zones if not z.get("district")]
            order.delivery_zone = (
                catch_all[0]["name"]
                if catch_all
                else governorate_zones[0]["name"]
            )
        else:
            frappe.throw(
                f"No enabled Delivery Zone found for Governorate '{order.governorate}' "
                f"{f'and District {order.district}' if order.district else ''}. "
                f"Please create a delivery zone for this location."
            )
            
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
            if not order.delivery_company or not order.delivery_company_name:
                    frappe.throw(f"Please set Delivery Company for Sales Order {order.sales_order} before printing the label.")
            if order.pick_list:
                    pl_barcode = self.create_barcode(order.pick_list)
                    order.picklist_barcode = pl_barcode
            if order.magento_id:
                magento_barcode = self.create_barcode(order.magento_id)
                order.magento_barcode = magento_barcode
            if order.delivery_method and order.delivery_method == "In-House":
                expected_delivery_company = frappe.db.get_value("Sales Order", order.sales_order, "custom_expected_delivery_company")
                expected_delivery_company_name = expected_delivery_company_map(expected_delivery_company)
                so_barcode = self.create_barcode(order.sales_order)
                order.order_barcode = so_barcode
                if expected_delivery_company_name and expected_delivery_company_name != order.delivery_company_name:
                    reassign_delivery_company(order.magento_id, order.delivery_company, self.doctype, self.name)
            elif order.delivery_method and order.delivery_method == "Outsourced":
                expected_delivery_company = frappe.db.get_value("Sales Order", order.sales_order, "custom_expected_delivery_company")
                expected_delivery_company_name = expected_delivery_company_map(expected_delivery_company)
                if expected_delivery_company_name and expected_delivery_company_name != order.delivery_company_name:
                    cont = reassign_delivery_company(order.magento_id, order.delivery_company, self.doctype, self.name)
                    if cont:
                        label_pdf = get_shipping_label(order.magento_id, self.doctype, self.name)
                        if label_pdf:
                            base64_image = create_label_attachment(label_pdf, self.doctype, self.name)
                            outsourced_label = f"data:image/png;base64,{base64_image}"
                            order.outsourced_label = outsourced_label
                elif expected_delivery_company_name and expected_delivery_company_name == order.delivery_company_name:
                    label_pdf = get_shipping_label(order.magento_id, self.doctype, self.name)
                    if label_pdf:
                        base64_image = create_label_attachment(label_pdf, self.doctype, self.name)
                        outsourced_label = f"data:image/png;base64,{base64_image}"
                        order.outsourced_label = outsourced_label
                    
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
    governorate_list = []

    if governorate:
        governorate = json.loads(governorate)
        governorate_list = [row.get("governorate") for row in governorate if row.get("governorate")]

    if not governorate_list:
        return {
            "orders": [],
            "grouped_orders": {},
            "zones": []
        }

    filters = {
        "delivery_date": delivery_date,
        "custom_delivery_time": delivery_time,
        "custom_magento_status": order_status,
        "custom_governorate": ["in", governorate_list],
        "docstatus": 1,
        "custom_manually": 0,
    }

    orders = frappe.get_all(
        "Sales Order",
        filters=filters,
        fields=[
            "name", "customer", "customer_name", "delivery_date",
            "custom_delivery_time", "grand_total",
            "custom_governorate", "custom_district",
            "total_qty", "customer_address", "custom_magento_id"
        ],
        order_by="custom_governorate, custom_district, name"
    )
    
    for order in orders:
        order["address"] = ""
        order["city"] = ""
        order["landmark"] = ""
        order["mobile_no"] = ""
        order["district"] = ""
        order["delivery_zone"] = ""

        if order.custom_magento_billing_address:
            billing_text = order.custom_magento_billing_address
            order["country"] = extract_value(billing_text, "Country")
            order["city"] = extract_value(billing_text, "City")
            order["district"] = extract_value(billing_text, "District")
            order["mobile_no"] = extract_value(billing_text, "Phone")
            
            order["customer_name"] = extract_value(billing_text, "Customer Name")
        if order.customer_address:
            address_doc = frappe.get_doc("Address", order.customer_address)

            order["address"] = order.get("city") or address_doc.address_line1
            order["city"] = order.get("country") or address_doc.city
            order["landmark"] = order.get("district") or address_doc.address_title
            order["mobile_no"] = order.get("mobile_no") or address_doc.phone

        delivery_zone = get_delivery_zone_for_order(
            order.get("custom_governorate"),
            order.get("custom_district")
        )
        
        order["delivery_zone"] = delivery_zone
        
        delivery_company, delivery_company_name, delivery_method = resolve_delivery_company(delivery_zone)

        order["delivery_company"] = delivery_company
        order["delivery_company_name"] = delivery_company_name
        order["delivery_method"] = delivery_method

    grouped_orders = {}
    for order in orders:
        zone = order.get("delivery_zone", "Unassigned")
        grouped_orders.setdefault(zone, []).append(order)

    return {
        "orders": orders,
        "grouped_orders": grouped_orders,
        "zones": list(grouped_orders.keys())
    }

def get_delivery_zone_for_order(governorate, district=None):
    if not governorate:
        return None

    dz = frappe.qb.DocType("Delivery Zone")
    dzg = frappe.qb.DocType("Governorate MultiSelect")
    dzd = frappe.qb.DocType("District MultiSelect")

    base_query = (
        frappe.qb.from_(dz)
        .join(dzg).on(
            (dzg.parent == dz.name) &
            (dzg.governorate == governorate)
        )
        .select(dz.name)
        .where(
            (dz.is_enabled == 1)
        )
    )

    if district:
        exact_zone = (
            base_query
            .join(dzd).on(
                (dzd.parent == dz.name) &
                (dzd.district == district)
            )
            .orderby(dz.creation, order=frappe.qb.desc)
            .limit(1)
            .run(as_dict=True)
        )
        if exact_zone:
            return exact_zone[0]["name"]

    governorate_zones = (
        base_query
        .orderby(dz.creation, order=frappe.qb.desc)
        .run(as_dict=True)
    )

    if governorate_zones:
        catch_all = [z for z in governorate_zones if not z.get("district")]
        if catch_all:
            return catch_all[0]["name"]
        return governorate_zones[0]["name"]

    return None
    
def reassign_delivery_company(magento_id, delivery_company, doctype, docname):
    base_url, headers = base_data("magento")

    post_url = f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/reassign"
    payload = {
        "incrementId": magento_id,
        "shippingMethod": delivery_company
    }

    response = request_with_history(
        req_method="POST",
        document=doctype,
        doctype=docname,
        url=post_url,
        headers=headers,
        payload=payload
    )

    if response.status_code != 200:
        frappe.throw(
            f"Failed to reassign shipping method for Magento ID {magento_id}. "
            f"Response: {response.text}"
        )

    return True

def get_shipping_label(magento_id, doctype, docname):
    base_url, headers = base_data("magento")

    get_url = f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/label/{magento_id}"

    response = request_with_history(
        req_method="GET",
        document=doctype,
        doctype=docname,
        url=get_url,
        headers=headers
    )

    if response.status_code != 200:
        frappe.throw(
            f"Failed to fetch label for Magento ID {magento_id}. "
            f"Response: {response.text}"
        )
    
    json_response = response.json()
    if not json_response.get("success"):
        frappe.throw(
            f"Label data not found for Magento ID {magento_id}. "
            f"Message: {json_response.get('message')}"
        )
    

    return json_response

def create_label_attachment(label_response, doctype, docname):
    label_url = label_response.get("label_url")
    if not label_url:
        frappe.throw("Label URL not found in response.")

    pdf_res = request_with_history(
        req_method="GET",
        document=doctype,
        doctype=docname,
        url=label_url,
    )

    if pdf_res.status_code != 200:
        frappe.throw(f"Failed to fetch PDF content from {label_url}")

    pdf_bytes = pdf_res.content

    base64_image = pdf_to_base64_image(pdf_bytes)

    file_name = f"Shipping-Label-{label_response.get('order_id')}-{now_datetime().strftime('%Y%m%d%H%M%S')}.pdf"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "file_url": label_url,
        "is_private": 0,
        "attached_to_doctype": doctype,
        "attached_to_name": docname
    })
    file_doc.save(ignore_permissions=True)

    return base64_image


def expected_delivery_company_map(expected_delivery_company):
    dc_map = {
        "Fleetroot": "Miraaya fleet",
        "Sandoog": "SANDOOK",
        "Boxy": "BOXY"
    }
    
    return dc_map.get(expected_delivery_company)

def resolve_delivery_company(delivery_zone):
    delivery_company = None
    delivery_company_name = None
    delivery_method = None

    if delivery_zone:
        dz = frappe.db.get_value(
            "Delivery Zone",
            delivery_zone,
            ["delivery_company", "delivery_company_name", "delivery_method"],
            as_dict=True
        )

        if dz:
            delivery_company = dz.delivery_company
            delivery_company_name = dz.delivery_company_name
            delivery_method = dz.delivery_method
            
    return delivery_company, delivery_company_name, delivery_method

def pdf_to_base64_image(pdf_bytes, page_number=0, image_format='PNG'):
    try:
        images = convert_from_bytes(pdf_bytes)

        if not images:
            return None

        img = images[page_number]

        buffer = io.BytesIO()
        img.save(buffer, format=image_format)
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode('utf-8')

    except Exception as e:
        frappe.log_error(f"PDF to image conversion failed: {str(e)}")
        return None
    
def extract_value(text, field):
    pattern = rf"- {field}:\s*(.*)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None