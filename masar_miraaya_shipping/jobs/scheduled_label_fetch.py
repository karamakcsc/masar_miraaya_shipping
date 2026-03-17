import frappe
import base64
from frappe.utils import today, add_days
from masar_miraaya_shipping.masar_miraaya_shipping.doctype.shipping_label_print.shipping_label_print import get_shipping_label, pdf_to_base64_image


def fetch_and_store_labels():
    """
    Runs every 30 minutes.
    Fetches shipping labels for Sales Orders created today or 2 days before
    where expected delivery company is NOT Fleetroot and label not yet stored.
    """
    yesterday = add_days(today(), -2)

    # Batch-fetch eligible orders in one query
    orders = frappe.get_all(
        "Sales Order",
        filters={
            "transaction_date":                        ["between", [yesterday, today()]],
            "custom_expected_delivery_company": ["!=", "Fleetroot"],
            "custom_expected_delivery_company": ["is", "set"],
            "custom_magento_id":               ["is", "set"],
            "docstatus":                       1,
        },
        fields=[
            "name",
            "custom_magento_id",
            "custom_expected_delivery_company",
            "custom_expected_dc_id",
        ],
    )

    if not orders:
        return

    # Exclude orders that already have a completed label image
    existing = {
        r.sales_order
        for r in frappe.get_all(
            "Shipping Label Image",
            filters={
                "sales_order": ["in", [o.name for o in orders]],
                "status":      "Completed",
            },
            fields=["sales_order"],
        )
    }

    pending = [o for o in orders if o.name not in existing]

    if not pending:
        return

    frappe.logger().info(f"[LabelFetch] Processing {len(pending)} orders.")

    for order in pending:
        _process_single_order(order)


def _process_single_order(order):
    """Fetch, convert, and store label for one Sales Order."""
    magento_id = order.custom_magento_id
    doctype    = "Shipping Label Image"

    # Upsert: get existing draft or create new
    existing_name = frappe.db.get_value(
        "Shipping Label Image",
        {"sales_order": order.name},
        "name",
    )

    if existing_name:
        doc = frappe.get_doc("Shipping Label Image", existing_name)
        # Skip if already completed
        if doc.status == "Completed":
            return
    else:
        doc = frappe.get_doc({
            "doctype":    "Shipping Label Image",
            "sales_order": order.name,
            "magento_id":  magento_id,
            "status":      "Pending",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

    try:
        frappe.db.set_value("Shipping Label Image", doc.name, "status", "Processing")
        frappe.db.commit()

        # Fetch label PDF from Magento
        label_response = get_shipping_label(
            magento_id,
            "Shipping Label Image",
            doc.name,
        )

        if not label_response:
            _mark_failed(doc.name, "Empty label response")
            return

        label_url = label_response.get("label_url")
        if not label_url:
            _mark_failed(doc.name, "No label_url in response")
            return

        # Fetch the actual PDF bytes
        from masar_miraaya.api import request_with_history
        pdf_res = request_with_history(
            req_method="GET",
            document="Shipping Label Image",
            doctype=doc.name,
            url=label_url,
        )

        if pdf_res.status_code != 200:
            _mark_failed(doc.name, f"PDF fetch failed: {pdf_res.status_code}")
            return

        # Convert PDF → base64 PNG
        base64_image = pdf_to_base64_image(pdf_res.content)
        if not base64_image:
            _mark_failed(doc.name, "PDF to image conversion returned None")
            return

        # Store result
        frappe.db.set_value(
            "Shipping Label Image",
            doc.name,
            {
                "base64_image": base64_image,       # Long Text field
                "label_url":    label_url,
                "status":       "Completed",
                "fetched_at":   frappe.utils.now_datetime(),
            },
        )
        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"[LabelFetch] Failed for SO {order.name} / Magento {magento_id}",
        )
        _mark_failed(doc.name, "Exception — see error log")


def _mark_failed(doc_name, reason):
    frappe.db.set_value(
        "Shipping Label Image",
        doc_name,
        {
            "status":        "Failed",
            "failure_reason": reason,       # Small Text field
        },
    )
    frappe.db.commit()