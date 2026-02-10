frappe.pages['order-delivery'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Order Delivery',
		single_column: true
	});

	let current_page = 1;
	const page_size = 8;

	let from_date = page.add_field({
	label: __('From Date'),
	fieldtype: 'Date',
	fieldname: 'from_date',
	onchange: function() {
		scanned_orders = {};
		scanned_order_keys = [];
		current_page = 1;
		fetch_existing_orders();
	}
	});

	let to_date = page.add_field({
		label: __('To Date'),
		fieldtype: 'Date',
		fieldname: 'to_date',
		onchange: function() {
			scanned_orders = {};
			scanned_order_keys = [];
			current_page = 1;
			fetch_existing_orders();
		}
	});

	let today = frappe.datetime.get_today();
	let week_ago = frappe.datetime.add_days(today, -7);

	from_date.set_value(week_ago);
	to_date.set_value(today);

	let driver = page.add_field({
		label: __('Driver'),
		fieldtype: 'Link',
		fieldname: 'driver',
		options: 'Driver',
		reqd: 1,
		onchange: function() {
			scanned_orders = {};
			scanned_order_keys = [];
			current_page = 1;
			fetch_existing_orders();
		}
	});

	let $container = $('<div class="driver-assignment-container"></div>').appendTo(page.main);

	let $barcode_section = $(`
		<div class="barcode-scanner" style="margin:20px 0;padding:15px;background:#f8f9fa;border-radius:5px;">
			<h4>Scan Sales Order</h4>
			<input type="text" class="form-control barcode-input"
				placeholder="Scan Sales Order..."
				autofocus>
		</div>
	`).appendTo($container);

	let $orders_container = $('<div class="scanned-orders"></div>').appendTo($container);

	let scanned_orders = {};
	let scanned_order_keys = [];

	function render_scanned_list() {
		$orders_container.empty();

		let keys = scanned_order_keys;
		let total_count = keys.length;

		if (total_count === 0) {
			$orders_container.append(
				'<p class="text-muted text-center">Scan sales orders to set as delivered</p>'
			);
			return;
		}

		let total_pages = Math.ceil(total_count / page_size);
		current_page = Math.max(1, Math.min(current_page, total_pages));

		let start = (current_page - 1) * page_size;
		let end = start + page_size;
		let page_keys = keys.slice(start, end);

		let $table = $(`
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>Sales Order</th>
						<th>Magento ID</th>
						<th>Status</th>
						<th>Customer</th>
						<th>Grand Total</th>
						<th>Contact No.</th>
						<th>Address</th>
						<th>Driver Name</th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		`);

		let $tbody = $table.find('tbody');

		page_keys.forEach(so => {
			let row = scanned_orders[so];
			$tbody.append(`
				<tr>
					<td><a href="/app/sales-order/${so}" target="_blank">${so}</a></td>
					<td>${row.magento_id || '-'}</td>
					<td>${row.magento_status || '-'}</td>
					<td>${row.customer}</td>
					<td>${row.grand_total}</td>
					<td>${row.contact_phone || '-'}</td>
					<td>${row.address_display || '-'}</td>
					<td>${row.driver}</td>
				</tr>
			`);
		});

		$orders_container.append($table);

		if (total_pages > 1) {
			let pagination = `<div class="text-center mt-3">`;

			if (current_page > 1) {
				pagination += `<button class="btn btn-default prev-page">Previous</button>`;
			}

			pagination += ` <span>Page ${current_page} of ${total_pages}</span> `;

			if (current_page < total_pages) {
				pagination += `<button class="btn btn-default next-page">Next</button>`;
			}

			pagination += `</div>`;
			$orders_container.append(pagination);
		}
	}

	$barcode_section.find('.barcode-input').on('keypress', function(e) {
		if (e.which !== 13) return;

		let scanned_value = $(this).val().trim();
		if (!scanned_value) return;

		if (scanned_orders[scanned_value]) {
			frappe.show_alert({
				message: __('Sales Order already scanned and dispatched'),
				indicator: 'orange'
			});
			$(this).val('');
			return;
		}

		if (from_date.get_value() && to_date.get_value()) {
			if (from_date.get_value() > to_date.get_value()) {
				frappe.msgprint({
					message: __('From Date cannot be after To Date'),
					indicator: 'red',
					title: __('Invalid Date Range')
				});
				return;
			}
		}

		if (!driver.get_value()) {
			frappe.msgprint({
				message: __('Please select a driver'),
				indicator: 'orange',
				title: __('Driver Required')
			});
			return;
		}
		
		const scan_errors = {
			not_on_the_way: __('Sales Order is not On the Way'),
			driver_mismatch: __('Sales Order is assigned to another driver'),
			no_pick_list: __('No submitted Pick List found'),
			invalid_sales_order: __('Invalid Sales Order'),
			already_delivered: __('Sales Order is already Delivered')
		};
		
		frappe.call({
			method: 'masar_miraaya_shipping.masar_miraaya_shipping.page.order_delivery.order_delivery.scan_and_set_delivered',
			args: {
				sales_order: scanned_value,
				driver: driver.get_value()
			},
			freeze: true,
			freeze_message: __('Setting as delivered...'),
			callback: function(r) {
				if (r.message.status === 'error') {
					frappe.show_alert({
						message: scan_errors[r.message.reason] || __('Sales Order cannot be set as delivered'),
						indicator: 'red'
					});
					return;
				}

				frappe.show_alert({
					message: __('Sales Order {0} set as delivered successfully', [r.message.data.sales_order]),
					indicator: 'green'
				});

				scanned_orders[r.message.data.sales_order] = r.message.data;
				if (!scanned_order_keys.includes(r.message.data.sales_order)) {
					scanned_order_keys.unshift(r.message.data.sales_order);
				}
				render_scanned_list();
			}
		});

		$(this).val('');
	});

	function fetch_existing_orders() {
		if (!driver.get_value()) return;

		frappe.call({
			method: 'masar_miraaya_shipping.masar_miraaya_shipping.page.order_delivery.order_delivery.get_delivered_orders',
			args: {
				driver: driver.get_value(),
				from_date: from_date.get_value(),
				to_date: to_date.get_value()
			},
			callback: function(r) {
				if (r.message && r.message.length) {
					scanned_orders = {};
					scanned_order_keys = [];
					r.message.forEach(order => {
						scanned_orders[order.sales_order] = order;
						scanned_order_keys.push(order.sales_order);
					});
					render_scanned_list();
				} else {
					scanned_orders = {};
					scanned_order_keys = [];
					render_scanned_list();
				}
			}
		});
	}

	fetch_existing_orders();

	$barcode_section.find('.barcode-input').focus();

	$orders_container.on('click', '.prev-page', function () {
		current_page--;
		render_scanned_list();
	});

	$orders_container.on('click', '.next-page', function () {
		current_page++;
		render_scanned_list();
	});

	page.add_inner_button(__('Refresh'), function() {
		frappe.show_alert({ message: __('Refreshing orders...'), indicator: 'blue' });

		fetch_existing_orders();

		$barcode_section.find('.barcode-input').val('').focus();
	});

};