# import frappe
# from frappe.model.document import Document
# import qrcode
# import io
# import base64
# from masar_miraaya.api import base_data, request_with_history
# from frappe.utils import now_datetime
# import json
# from pdf2image import convert_from_bytes
# import re


# # ── Module-level compiled regex for billing address parsing ──────────────────
# _BILLING_FIELDS = ["Country", "City", "District", "Landmark", "Address", "Phone", "Customer Name"]
# _BILLING_PATTERNS = {
#     field: re.compile(rf"- {field}:\s*(.*)", re.IGNORECASE)
#     for field in _BILLING_FIELDS
# }

# def _extract_billing(text, field):
#     m = _BILLING_PATTERNS[field].search(text)
#     return m.group(1).strip() if m else None


# class ShippingLabelPrint(Document):
#     def validate(self):
#         self.total_orders = len(self.orders)

#         # ── Batch-fetch SO location data ─────────────────────────────────────
#         so_names = [o.sales_order for o in self.orders if o.sales_order]
#         so_data = {}
#         if so_names:
#             rows = frappe.get_all(
#                 "Sales Order",
#                 filters={"name": ["in", so_names]},
#                 fields=["name", "custom_governorate", "custom_district"]
#             )
#             so_data = {r.name: r for r in rows}

#         for order in self.orders:
#             if order.sales_order and order.sales_order in so_data:
#                 so = so_data[order.sales_order]
#                 if so.custom_governorate:
#                     order.governorate = so.custom_governorate
#                 if so.custom_district:
#                     order.district = so.custom_district

#         # ── Batch delivery zone assignment (eliminates N+1 in validate) ──────
#         unique_pairs = list({(o.governorate, o.district or None) for o in self.orders})
#         zone_cache = {pair: _get_delivery_zone(*pair) for pair in unique_pairs}

#         for order in self.orders:
#             pair = (order.governorate, order.district or None)
#             zone = zone_cache.get(pair)
#             if zone:
#                 order.delivery_zone = zone
#             elif not order.delivery_zone:
#                 frappe.throw(
#                     f"No enabled Delivery Zone found for Governorate '{order.governorate}'"
#                     f"{f' and District {order.district}' if order.district else ''}. "
#                     f"Please create a delivery zone for this location."
#                 )

#     def on_submit(self):
#         if not self.orders:
#             frappe.throw("Please add at least one order to print shipping label.")
#         if not self.printed_by:
#             self.printed_by = frappe.session.user
#         self.print_status = "Queued"
#         frappe.enqueue_doc(
#             self.doctype,
#             self.name,
#             "generate_qrcodes",
#             queue="long",
#             timeout=3000
#         )

#     def on_cancel(self):
#         self.print_status = "Cancelled"
#         for order in self.orders:
#             order.qr_active = 0

#     def _set_shipping_details_pl(self):
#         """Bulk-update Sales Order delivery zones in one pass (no loop DB writes)."""
#         so_updates = {
#             order.sales_order: order.delivery_zone or ""
#             for order in self.orders
#             if order.sales_order
#         }
#         for so_name, zone in so_updates.items():
#             frappe.db.set_value("Sales Order", so_name, "custom_delivery_zone", zone)

#     def generate_qrcodes(self):
#         try:
#             self.reload()
#             self._set_shipping_details_pl()

#             # ── Batch-fetch expected delivery company data ────────────────────
#             sales_orders = [o.sales_order for o in self.orders]
#             so_rows = frappe.get_all(
#                 "Sales Order",
#                 filters={"name": ["in", sales_orders]},
#                 fields=["name", "custom_expected_delivery_company", "custom_expected_dc_id"]
#             )
#             so_map = {d.name: d for d in so_rows}

#             for order in self.orders:
#                 if not order.delivery_company or not order.delivery_company_name:
#                     frappe.throw(
#                         f"Please set Delivery Company for Sales Order "
#                         f"{order.sales_order} before printing the label."
#                     )

#                 if order.magento_id:
#                     order.magento_barcode = self._create_qrcode(order.magento_id)

#                 so_values = so_map.get(order.sales_order)
#                 expected_dc_name = (
#                     so_values.custom_expected_dc_id
#                     or _expected_delivery_company_map(so_values.custom_expected_delivery_company)
#                 )

#                 if order.delivery_method == "In-House":
#                     order.order_barcode = self._create_qrcode(order.sales_order)
#                     if expected_dc_name and expected_dc_name != order.delivery_company_name:
#                         reassign_delivery_company(
#                             order.magento_id, order.delivery_company,
#                             self.doctype, self.name
#                         )

#                 elif order.delivery_method == "Outsourced":
#                     needs_reassign = (
#                         expected_dc_name and expected_dc_name != order.delivery_company_name
#                     )
#                     if needs_reassign:
#                         cont = reassign_delivery_company(
#                             order.magento_id, order.delivery_company,
#                             self.doctype, self.name
#                         )
#                         if not cont:
#                             continue

#                     label_pdf = get_shipping_label(order.magento_id, self.doctype, self.name)
#                     if label_pdf:
#                         base64_image = create_label_attachment(label_pdf, self.doctype, self.name)
#                         order.outsourced_label = f"data:image/png;base64,{base64_image}"

#             self.print_status = "Printed"
#         except Exception:
#             frappe.log_error(frappe.get_traceback(), "Shipping Label QR Generation Failed")
#             self.print_status = "Failed"

#         self.flags.ignore_version = True
#         self.save(ignore_permissions=True)

#     def _create_qrcode(self, text):
#         """Generate a QR code and return it as a base64 data URI."""
#         try:
#             qr = qrcode.QRCode(
#                 version=1,
#                 error_correction=qrcode.constants.ERROR_CORRECT_M,
#                 box_size=15,
#                 border=4,
#             )
#             qr.add_data(text)
#             qr.make(fit=True)
#             img = qr.make_image(fill_color="black", back_color="white")

#             buffer = io.BytesIO()
#             img.save(buffer, format="PNG")
#             # getvalue() avoids the seek(0)+read() dance
#             return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"

#         except Exception as e:
#             frappe.log_error(f"QR code generation failed for {text}: {str(e)}")
#             return None

#     # Keep old name as alias so any external callers don't break
#     create_qrcode = _create_qrcode

#     @frappe.whitelist()
#     def mark_as_printed(self):
#         for order in self.orders:
#             order.label_printed = 1
#             order.print_count = (order.print_count or 0) + 1

#         self.print_status = "Reprinted" if self.print_status == "Printed" else "Printed"
#         self.flags.ignore_version = True
#         self.save()
#         return True


# # ── Whitelisted API ──────────────────────────────────────────────────────────

# @frappe.whitelist()
# def get_filtered_orders(delivery_date, delivery_time, governorate, order_status):
#     governorate_list = []
#     if governorate:
#         governorate = json.loads(governorate)
#         governorate_list = [row.get("governorate") for row in governorate if row.get("governorate")]

#     if not governorate_list:
#         return {"orders": [], "grouped_orders": {}, "zones": []}

#     orders = frappe.get_all(
#         "Sales Order",
#         filters={
#             "delivery_date": delivery_date,
#             "custom_delivery_time": delivery_time,
#             "custom_magento_status": order_status,
#             "custom_governorate": ["in", governorate_list],
#             "docstatus": 1,
#             "custom_manually": 0,
#         },
#         fields=[
#             "name", "customer", "customer_name", "delivery_date",
#             "custom_delivery_time", "grand_total",
#             "custom_governorate", "custom_district",
#             "total_qty", "customer_address", "custom_magento_id",
#             "custom_is_cash_on_delivery", "custom_payment_channel_amount",
#             "custom_magento_billing_address", "contact_mobile"
#         ],
#         order_by="custom_governorate, custom_district, name"
#     )

#     if not orders:
#         return {"orders": [], "grouped_orders": {}, "zones": []}

#     # ── 1. Batch-fetch Address docs ──────────────────────────────────────────
#     address_names = list({o.customer_address for o in orders if o.customer_address})
#     address_map = {}
#     if address_names:
#         address_map = {
#             r.name: r
#             for r in frappe.get_all(
#                 "Address",
#                 filters={"name": ["in", address_names]},
#                 fields=["name", "address_line1", "city", "address_title"]
#             )
#         }

#     # ── 2. Resolve delivery zones for unique (governorate, district) pairs ───
#     unique_pairs = list({(o.custom_governorate, o.custom_district or None) for o in orders})
#     zone_cache = {pair: _get_delivery_zone(*pair) for pair in unique_pairs}

#     # ── 3. Batch-fetch Delivery Zone details ─────────────────────────────────
#     resolved_zones = list({z for z in zone_cache.values() if z})
#     dz_map = {}
#     if resolved_zones:
#         dz_map = {
#             r.name: r
#             for r in frappe.get_all(
#                 "Delivery Zone",
#                 filters={"name": ["in", resolved_zones]},
#                 fields=["name", "delivery_company", "delivery_company_name", "delivery_method"]
#             )
#         }

#     # ── 4. Enrich orders (zero additional DB hits) ───────────────────────────
#     for order in orders:
#         cod     = order.custom_is_cash_on_delivery
#         prepaid = order.custom_payment_channel_amount
#         if cod and prepaid:
#             payment_method = "Cash on Delivery / Prepaid"
#         elif cod:
#             payment_method = "Cash on Delivery"
#         elif prepaid:
#             payment_method = "Prepaid"
#         else:
#             payment_method = ""

#         country = city = district = landmark = address = mobile_no = ""
#         customer_name = order.customer_name

#         billing_text = order.custom_magento_billing_address
#         if billing_text:
#             country       = _extract_billing(billing_text, "Country") or ""
#             city          = _extract_billing(billing_text, "City") or ""
#             district      = _extract_billing(billing_text, "District") or ""
#             landmark      = _extract_billing(billing_text, "Landmark") or ""
#             address       = _extract_billing(billing_text, "Address") or ""
#             mobile_no     = _extract_billing(billing_text, "Phone") or ""
#             customer_name = _extract_billing(billing_text, "Customer Name") or customer_name

#         if order.customer_address:
#             addr = address_map.get(order.customer_address)
#             if addr:
#                 address       = address   or addr.address_line1 or ""
#                 city          = city      or addr.city or ""
#                 landmark      = landmark  or addr.address_title or ""
#                 mobile_no     = mobile_no or order.contact_mobile or ""

#         delivery_zone = zone_cache.get((order.custom_governorate, order.custom_district or None))

#         delivery_company = delivery_company_name = delivery_method = None
#         if delivery_zone:
#             dz = dz_map.get(delivery_zone)
#             if dz:
#                 delivery_company      = dz.delivery_company
#                 delivery_company_name = dz.delivery_company_name
#                 delivery_method       = dz.delivery_method

#         order.update({
#             "country":               country,
#             "address":               address,
#             "city":                  city,
#             "district":              district,
#             "landmark":              landmark,
#             "mobile_no":             mobile_no,
#             "customer_name":         customer_name,
#             "payment_method":        payment_method,
#             "delivery_zone":         delivery_zone,
#             "delivery_company":      delivery_company,
#             "delivery_company_name": delivery_company_name,
#             "delivery_method":       delivery_method,
#         })

#     # ── 5. Group by zone ─────────────────────────────────────────────────────
#     grouped_orders = {}
#     for order in orders:
#         zone = order.get("delivery_zone") or "Unassigned"
#         grouped_orders.setdefault(zone, []).append(order)

#     return {
#         "orders": orders,
#         "grouped_orders": grouped_orders,
#         "zones": list(grouped_orders.keys()),
#     }


# # ── Shared helpers ───────────────────────────────────────────────────────────

# def _get_delivery_zone(governorate, district=None):
#     """
#     Resolve the best matching Delivery Zone for a (governorate, district) pair.
#     Consolidated into a single helper used by both validate() and get_filtered_orders()
#     so the logic is never duplicated.
#     """
#     if not governorate:
#         return None

#     dz  = frappe.qb.DocType("Delivery Zone")
#     dzg = frappe.qb.DocType("Governorate MultiSelect")
#     dzd = frappe.qb.DocType("District MultiSelect")

#     base_query = (
#         frappe.qb.from_(dz)
#         .join(dzg).on((dzg.parent == dz.name) & (dzg.governorate == governorate))
#         .select(dz.name)
#         .where(dz.is_enabled == 1)
#         .orderby(dz.creation, order=frappe.qb.desc)
#     )

#     if district:
#         exact = (
#             base_query
#             .join(dzd).on((dzd.parent == dz.name) & (dzd.district == district))
#             .limit(1)
#             .run(as_dict=True)
#         )
#         if exact:
#             return exact[0]["name"]

#     zones = base_query.run(as_dict=True)
#     if not zones:
#         return None

#     catch_all = [z for z in zones if not z.get("district")]
#     return catch_all[0]["name"] if catch_all else zones[0]["name"]


# # Keep old public name for any existing call sites
# get_delivery_zone_for_order = _get_delivery_zone


# def reassign_delivery_company(magento_id, delivery_company, doctype, docname):
#     base_url, headers = base_data("magento")
#     response = request_with_history(
#         req_method="POST",
#         document=doctype,
#         doctype=docname,
#         url=f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/reassign",
#         headers=headers,
#         payload={"incrementId": magento_id, "shippingMethod": delivery_company}
#     )
#     if response.status_code != 200:
#         frappe.throw(
#             f"Failed to reassign shipping method for Magento ID {magento_id}. "
#             f"Response: {response.text}"
#         )
#     return True


# def get_shipping_label(magento_id, doctype, docname):
#     base_url, headers = base_data("magento")
#     response = request_with_history(
#         req_method="GET",
#         document=doctype,
#         doctype=docname,
#         url=f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/label/{magento_id}",
#         headers=headers
#     )
#     if response.status_code != 200:
#         frappe.throw(
#             f"Failed to fetch label for Magento ID {magento_id}. "
#             f"Response: {response.text}"
#         )
#     json_response = response.json()
#     if not json_response.get("success"):
#         frappe.throw(
#             f"Label data not found for Magento ID {magento_id}. "
#             f"Message: {json_response.get('message')}"
#         )
#     return json_response


# def create_label_attachment(label_response, doctype, docname):
#     label_url = label_response.get("label_url")
#     if not label_url:
#         frappe.throw("Label URL not found in response.")

#     pdf_res = request_with_history(
#         req_method="GET",
#         document=doctype,
#         doctype=docname,
#         url=label_url,
#     )
#     if pdf_res.status_code != 200:
#         frappe.throw(f"Failed to fetch PDF content from {label_url}")

#     base64_image = pdf_to_base64_image(pdf_res.content)

#     file_doc = frappe.get_doc({
#         "doctype": "File",
#         "file_name": f"Shipping-Label-{label_response.get('order_id')}-{now_datetime().strftime('%Y%m%d%H%M%S')}.pdf",
#         "file_url": label_url,
#         "is_private": 0,
#         "attached_to_doctype": doctype,
#         "attached_to_name": docname
#     })
#     file_doc.save(ignore_permissions=True)

#     return base64_image


# def _expected_delivery_company_map(expected_delivery_company):
#     return {
#         "Fleetroot": "Miraaya fleet",
#         "Sandoog":   "SANDOOK",
#         "Boxy":      "BOXY",
#     }.get(expected_delivery_company)

# # Keep old public name
# expected_delivery_company_map = _expected_delivery_company_map


# def resolve_delivery_company(delivery_zone):
#     if not delivery_zone:
#         return None, None, None
#     dz = frappe.db.get_value(
#         "Delivery Zone",
#         delivery_zone,
#         ["delivery_company", "delivery_company_name", "delivery_method"],
#         as_dict=True
#     )
#     if dz:
#         return dz.delivery_company, dz.delivery_company_name, dz.delivery_method
#     return None, None, None


# def pdf_to_base64_image(pdf_bytes, page_number=0, image_format="PNG"):
#     try:
#         images = convert_from_bytes(pdf_bytes, dpi=200)
#         if not images:
#             return None
#         buffer = io.BytesIO()
#         images[page_number].save(buffer, format=image_format)
#         return base64.b64encode(buffer.getvalue()).decode("utf-8")
#     except Exception as e:
#         frappe.log_error(f"PDF to image conversion failed: {str(e)}")
#         return None


import frappe
from frappe.model.document import Document
import qrcode
import io
import base64
from masar_miraaya.api import base_data, request_with_history
from frappe.utils import now_datetime
import json
from pdf2image import convert_from_bytes
import re


# ---------------------------------------------------------------------------
# Module-level compiled regex patterns (compiled once, reused forever)
# ---------------------------------------------------------------------------

_BILLING_FIELDS = [
    "Country",
    "City",
    "District",
    "Landmark",
    "Address",
    "Phone",
    "Customer Name",
]

_BILLING_PATTERNS = {
    field: re.compile(rf"- {field}:\s*(.*)", re.IGNORECASE)
    for field in _BILLING_FIELDS
}


def _extract_billing(text, field):
    """Extract a single field from a billing address text block."""
    m = _BILLING_PATTERNS[field].search(text)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Delivery zone resolution
# ---------------------------------------------------------------------------

def _resolve_zone(governorate, district=None):
    """
    Return the best matching Delivery Zone name for a (governorate, district) pair.

    Priority (identical to original):
      1. Exact match on both governorate + district  → most recently created wins
      2. Governorate-only zone with no district rows → catch-all, most recent wins
      3. Any governorate zone                        → most recent wins
      4. None found                                  → return None
    """
    if not governorate:
        return None

    dz  = frappe.qb.DocType("Delivery Zone")
    dzg = frappe.qb.DocType("Governorate MultiSelect")
    dzd = frappe.qb.DocType("District MultiSelect")

    # Base: zones that serve this governorate, newest first
    base_query = (
        frappe.qb.from_(dz)
        .join(dzg).on(
            (dzg.parent == dz.name) &
            (dzg.governorate == governorate)
        )
        .select(dz.name)
        .where(dz.is_enabled == 1)
        .orderby(dz.creation, order=frappe.qb.desc)
    )

    # Step 1 — exact district match
    if district:
        exact = (
            base_query
            .join(dzd).on(
                (dzd.parent == dz.name) &
                (dzd.district == district)
            )
            .limit(1)
            .run(as_dict=True)
        )
        if exact:
            return exact[0]["name"]

    # Step 2 & 3 — fallback to governorate-level zones
    gov_zones = base_query.run(as_dict=True)
    if not gov_zones:
        return None

    catch_all = [z for z in gov_zones if not z.get("district")]
    return catch_all[0]["name"] if catch_all else gov_zones[0]["name"]


def _build_zone_cache(pairs):
    """
    Resolve delivery zones for a set of (governorate, district) pairs.
    Calls _resolve_zone once per *unique* pair — not once per order.
    """
    return {pair: _resolve_zone(*pair) for pair in pairs}


# ---------------------------------------------------------------------------
# Document class
# ---------------------------------------------------------------------------

class ShippingLabelPrint(Document):

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------

    def validate(self):
        self.total_orders = len(self.orders)

        # Batch-fetch SO location data (one query, not N)
        so_names = [o.sales_order for o in self.orders if o.sales_order]
        so_data  = {}
        if so_names:
            rows   = frappe.get_all(
                "Sales Order",
                filters={"name": ["in", so_names]},
                fields=["name", "custom_governorate", "custom_district"],
            )
            so_data = {r.name: r for r in rows}

        # Copy governorate / district from SO onto each order row
        for order in self.orders:
            if order.sales_order and order.sales_order in so_data:
                so = so_data[order.sales_order]
                if so.custom_governorate:
                    order.governorate = so.custom_governorate
                if so.custom_district:
                    order.district    = so.custom_district

        # Build zone cache for unique pairs (eliminates N+1 in validate)
        unique_pairs = {
            (o.governorate, o.district or None)
            for o in self.orders
        }
        zone_cache = _build_zone_cache(unique_pairs)

        # Assign delivery zones — preserve original throw behaviour
        for order in self.orders:
            if not order.governorate:
                frappe.throw(
                    f"Governorate not found for Sales Order {order.sales_order}"
                )

            pair = (order.governorate, order.district or None)
            zone = zone_cache.get(pair)

            if zone:
                order.delivery_zone = zone
            elif not order.delivery_zone:
                frappe.throw(
                    f"No enabled Delivery Zone found for Governorate "
                    f"'{order.governorate}'"
                    + (
                        f" and District {order.district}"
                        if order.district else ""
                    )
                    + ". Please create a delivery zone for this location."
                )

    # ------------------------------------------------------------------
    # on_submit
    # ------------------------------------------------------------------

    def on_submit(self):
        if not self.orders:
            frappe.throw("Please add at least one order to print shipping label.")
        if not self.printed_by:
            self.printed_by = frappe.session.user
        self.print_status = "Queued"
        frappe.enqueue_doc(
            self.doctype,
            self.name,
            "generate_qrcodes",
            queue="long",
            timeout=3000,
        )

    # ------------------------------------------------------------------
    # on_cancel
    # ------------------------------------------------------------------

    def on_cancel(self):
        self.print_status = "Cancelled"
        for order in self.orders:
            order.qr_active = 0

    # ------------------------------------------------------------------
    # set_shipping_details_pl  (internal helper)
    # ------------------------------------------------------------------

    def set_shipping_details_pl(self):
        so_updates = {
            order.sales_order: order.delivery_zone or ""
            for order in self.orders
            if order.sales_order
        }
        for so_name, zone in so_updates.items():
            frappe.db.set_value(
                "Sales Order", so_name, "custom_delivery_zone", zone
            )

    # ------------------------------------------------------------------
    # generate_qrcodes  (background job)
    # ------------------------------------------------------------------

    def generate_qrcodes(self):
        try:
            # Always reload from DB first — this runs in a background queue
            self.reload()
            self.set_shipping_details_pl()

            # Batch-fetch expected delivery company fields (one query)
            sales_orders = [o.sales_order for o in self.orders]
            so_rows = frappe.get_all(
                "Sales Order",
                filters={"name": ["in", sales_orders]},
                fields=[
                    "name",
                    "custom_expected_delivery_company",
                    "custom_expected_dc_id",
                ],
            )
            so_map = {d.name: d for d in so_rows}

            for order in self.orders:

                # Guard: delivery company must be set
                if not order.delivery_company or not order.delivery_company_name:
                    frappe.throw(
                        f"Please set Delivery Company for Sales Order "
                        f"{order.sales_order} before printing the label."
                    )

                # QR for Magento ID
                if order.magento_id:
                    order.magento_barcode = self.create_qrcode(order.magento_id)

                so_values = so_map.get(order.sales_order)

                expected_delivery_company_name = expected_delivery_company_map(
                    so_values.custom_expected_delivery_company
                )
                expected_dc_name = (
                    so_values.custom_expected_dc_id
                    or expected_delivery_company_name
                )

                # ── In-House ──────────────────────────────────────────────
                if order.delivery_method and order.delivery_method == "In-House":

                    so_qrcode = self.create_qrcode(order.sales_order)
                    order.order_barcode = so_qrcode

                    if expected_dc_name and expected_dc_name != order.delivery_company_name:
                        reassign_delivery_company(
                            order.magento_id,
                            order.delivery_company,
                            self.doctype,
                            self.name,
                        )

                # ── Outsourced ────────────────────────────────────────────
                elif order.delivery_method and order.delivery_method == "Outsourced":

                    if expected_dc_name and expected_dc_name != order.delivery_company_name:
                        # Reassign first; only fetch label if reassign succeeded
                        cont = reassign_delivery_company(
                            order.magento_id,
                            order.delivery_company,
                            self.doctype,
                            self.name,
                        )
                        if cont:
                            label_pdf = get_shipping_label(
                                order.magento_id, self.doctype, self.name
                            )
                            if label_pdf:
                                base64_image = create_label_attachment(
                                    label_pdf, self.doctype, self.name
                                )
                                order.outsourced_label = (
                                    f"data:image/png;base64,{base64_image}"
                                )

                    elif (
                        expected_dc_name
                        and expected_dc_name == order.delivery_company_name
                    ):
                        # No reassign needed — fetch label directly
                        label_pdf = get_shipping_label(
                            order.magento_id, self.doctype, self.name
                        )
                        if label_pdf:
                            base64_image = create_label_attachment(
                                label_pdf, self.doctype, self.name
                            )
                            order.outsourced_label = (
                                f"data:image/png;base64,{base64_image}"
                            )

            self.print_status = "Printed"

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Shipping Label QR Generation Failed",
            )
            self.print_status = "Failed"

        self.flags.ignore_version = True
        self.save(ignore_permissions=True)

    # ------------------------------------------------------------------
    # create_qrcode
    # ------------------------------------------------------------------

    def create_qrcode(self, text):
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=15,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)

            img    = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")

            # getvalue() is equivalent to seek(0)+read() — avoids redundant seek
            return (
                "data:image/png;base64,"
                + base64.b64encode(buffer.getvalue()).decode("utf-8")
            )

        except Exception as e:
            frappe.log_error(
                f"QR code generation failed for {text}: {str(e)}"
            )
            return None

    # ------------------------------------------------------------------
    # mark_as_printed
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def mark_as_printed(self):
        for order in self.orders:
            order.label_printed = 1
            order.print_count   = (order.print_count or 0) + 1

        if self.print_status == "Printed":
            self.print_status = "Reprinted"
        else:
            self.print_status = "Printed"

        self.flags.ignore_version = True
        self.save()
        return True


# ---------------------------------------------------------------------------
# Whitelisted API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_filtered_orders(delivery_date, delivery_time, governorate, order_status):

    governorate_list = []
    if governorate:
        governorate      = json.loads(governorate)
        governorate_list = [
            row.get("governorate")
            for row in governorate
            if row.get("governorate")
        ]

    if not governorate_list:
        return {"orders": [], "grouped_orders": {}, "zones": []}

    orders = frappe.get_all(
        "Sales Order",
        filters={
            "delivery_date":          delivery_date,
            "custom_delivery_time":   delivery_time,
            "custom_magento_status":  order_status,
            "custom_governorate":     ["in", governorate_list],
            "docstatus":              1,
            "custom_manually":        0,
        },
        fields=[
            "name", "customer", "customer_name", "delivery_date",
            "custom_delivery_time", "grand_total",
            "custom_governorate", "custom_district",
            "total_qty", "customer_address", "custom_magento_id",
            "custom_is_cash_on_delivery", "custom_payment_channel_amount",
            "custom_magento_billing_address", "contact_mobile",
        ],
        order_by="custom_governorate, custom_district, name",
    )

    if not orders:
        return {"orders": [], "grouped_orders": {}, "zones": []}

    # ── 1. Batch-fetch all Address docs (one query) ──────────────────────────
    address_names = list({o.customer_address for o in orders if o.customer_address})
    address_map   = {}
    if address_names:
        address_map = {
            r.name: r
            for r in frappe.get_all(
                "Address",
                filters={"name": ["in", address_names]},
                fields=["name", "address_line1", "city", "address_title"],
            )
        }

    # ── 2. Resolve delivery zones for unique pairs (N queries → unique-pair queries) ──
    unique_pairs = {
        (o.custom_governorate, o.custom_district or None)
        for o in orders
    }
    zone_cache = _build_zone_cache(unique_pairs)

    # ── 3. Batch-fetch Delivery Zone details (one query) ────────────────────
    resolved_zones = list({z for z in zone_cache.values() if z})
    dz_map         = {}
    if resolved_zones:
        dz_map = {
            r.name: r
            for r in frappe.get_all(
                "Delivery Zone",
                filters={"name": ["in", resolved_zones]},
                fields=[
                    "name",
                    "delivery_company",
                    "delivery_company_name",
                    "delivery_method",
                ],
            )
        }

    # ── 4. Enrich every order row (zero additional DB hits) ─────────────────
    for order in orders:

        # Initialise all fields the original code set
        order["address"]      = ""
        order["city"]         = ""
        order["landmark"]     = ""
        order["mobile_no"]    = ""
        order["district"]     = ""
        order["delivery_zone"]          = ""
        order["delivery_company"]       = None
        order["delivery_company_name"]  = None
        order["delivery_method"]        = None
        order["payment_method"]         = ""
        order["country"]                = ""

        # Payment method (same logic as original)
        if order.custom_is_cash_on_delivery and order.custom_payment_channel_amount:
            order["payment_method"] = "Cash on Delivery / Prepaid"
        elif order.custom_is_cash_on_delivery:
            order["payment_method"] = "Cash on Delivery"
        elif order.custom_payment_channel_amount:
            order["payment_method"] = "Prepaid"

        # Billing address fields (same priority: billing text first)
        if order.custom_magento_billing_address:
            billing_text = order.custom_magento_billing_address
            order["country"]       = _extract_billing(billing_text, "Country") or ""
            order["city"]          = _extract_billing(billing_text, "City") or ""
            order["district"]      = _extract_billing(billing_text, "District") or ""
            order["landmark"]      = _extract_billing(billing_text, "Landmark") or ""
            order["address"]       = _extract_billing(billing_text, "Address") or ""
            order["mobile_no"]     = _extract_billing(billing_text, "Phone") or ""
            order["customer_name"] = (
                _extract_billing(billing_text, "Customer Name")
                or order.customer_name
            )

        # Fallback to Address doc (already in memory — no DB hit)
        if order.customer_address:
            addr = address_map.get(order.customer_address)
            if addr:
                order["address"]   = order.get("address")   or addr.address_line1 or ""
                order["city"]      = order.get("city")       or addr.city          or ""
                order["landmark"]  = order.get("landmark")   or addr.address_title or ""
                order["mobile_no"] = order.get("mobile_no")  or order.contact_mobile or ""

        # Delivery zone from cache
        delivery_zone = zone_cache.get(
            (order.custom_governorate, order.custom_district or None)
        )
        order["delivery_zone"] = delivery_zone

        # Delivery company from pre-fetched map
        if delivery_zone and delivery_zone in dz_map:
            dz = dz_map[delivery_zone]
            order["delivery_company"]      = dz.delivery_company
            order["delivery_company_name"] = dz.delivery_company_name
            order["delivery_method"]       = dz.delivery_method

    # ── 5. Group by zone ─────────────────────────────────────────────────────
    grouped_orders = {}
    for order in orders:
        zone = order.get("delivery_zone") or "Unassigned"
        grouped_orders.setdefault(zone, []).append(order)

    return {
        "orders":         orders,
        "grouped_orders": grouped_orders,
        "zones":          list(grouped_orders.keys()),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_delivery_zone_for_order(governorate, district=None):
    """Public alias kept for backwards compatibility."""
    return _resolve_zone(governorate, district)


def reassign_delivery_company(magento_id, delivery_company, doctype, docname):
    base_url, headers = base_data("magento")

    response = request_with_history(
        req_method="POST",
        document=doctype,
        doctype=docname,
        url=f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/reassign",
        headers=headers,
        payload={
            "incrementId":    magento_id,
            "shippingMethod": delivery_company,
        },
    )

    if response.status_code != 200:
        frappe.throw(
            f"Failed to reassign shipping method for Magento ID {magento_id}. "
            f"Response: {response.text}"
        )

    return True


def get_shipping_label(magento_id, doctype, docname):
    base_url, headers = base_data("magento")

    response = request_with_history(
        req_method="GET",
        document=doctype,
        doctype=docname,
        url=f"{base_url.rstrip('/')}/rest/V1/miraaya/shipping/order/label/{magento_id}",
        headers=headers,
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

    base64_image = pdf_to_base64_image(pdf_res.content)

    file_name = (
        f"Shipping-Label-{label_response.get('order_id')}"
        f"-{now_datetime().strftime('%Y%m%d%H%M%S')}.pdf"
    )
    file_doc = frappe.get_doc({
        "doctype":              "File",
        "file_name":            file_name,
        "file_url":             label_url,
        "is_private":           0,
        "attached_to_doctype":  doctype,
        "attached_to_name":     docname,
    })
    file_doc.save(ignore_permissions=True)

    return base64_image


def expected_delivery_company_map(expected_delivery_company):
    return {
        "Fleetroot": "Miraaya fleet",
        "Sandoog":   "SANDOOK",
        "Boxy":      "BOXY",
    }.get(expected_delivery_company)


def resolve_delivery_company(delivery_zone):
    """Kept for any external callers — uses batch-safe db.get_value."""
    delivery_company      = None
    delivery_company_name = None
    delivery_method       = None

    if delivery_zone:
        dz = frappe.db.get_value(
            "Delivery Zone",
            delivery_zone,
            ["delivery_company", "delivery_company_name", "delivery_method"],
            as_dict=True,
        )
        if dz:
            delivery_company      = dz.delivery_company
            delivery_company_name = dz.delivery_company_name
            delivery_method       = dz.delivery_method

    return delivery_company, delivery_company_name, delivery_method


def pdf_to_base64_image(pdf_bytes, page_number=0, image_format="PNG"):
    try:
        images = convert_from_bytes(pdf_bytes, dpi=200)
        if not images:
            return None

        buffer = io.BytesIO()
        images[page_number].save(buffer, format=image_format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    except Exception as e:
        frappe.log_error(f"PDF to image conversion failed: {str(e)}")
        return None