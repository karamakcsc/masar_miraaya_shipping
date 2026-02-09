frappe.pages['order-delivery'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Order Delivery',
		single_column: true
	});
	let $container = $('<div class="driver-assignment-container"></div>').appendTo(page.main);

	let $barcode_section = $(`
		<div class="barcode-scanner" style="margin:20px 0;padding:15px;background:#f8f9fa;border-radius:5px;">
			<h4>Scan Sales Order</h4>
			<input type="text" class="form-control barcode-input"
				placeholder="Scan Sales Order or Magento ID..."
				autofocus>
		</div>
	`).appendTo($container);

	let $orders_container = $('<div class="scanned-orders"></div>').appendTo($container);

	let scanned_orders = {};

	function render_scanned_list() {
		$orders_container.empty();

		let keys = Object.keys(scanned_orders);
		if (keys.length === 0) {
			$orders_container.append('<p class="text-muted text-center">Scan sales orders</p>');
			return;
		}

		let $table = $(`
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>Sales Order</th>
						<th>Magento ID</th>
						<th>Customer</th>
						<th>Grand Total</th>
						<th>Contact No.</th>
						<th>Address</th>
						<th>Delivery Company</th>
						<th>Driver Name</th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>
		`);

		let $tbody = $table.find('tbody');

		keys.forEach(so => {
			let row = scanned_orders[so];

			$tbody.append(`
				<tr>
					<td><a href="/app/sales-order/${so}" target="_blank">${so}</a></td>
					<td>${row.magento_id || '-'}</td>
					<td>${row.customer}</td>
					<td>${row.grand_total}</td>
					<td>${row.contact_phone || '-'}</td>
					<td>${row.address_display || '-'}</td>
					<td>${row.delivery_company}</td>
					<td>${row.driver}</td>
				</tr>
			`);
		});

		$orders_container.append($table);

		$orders_container.append(`
			<div class="text-right">
				<button class="btn btn-primary assign-driver-btn">
					Set as Delivered
				</button>
			</div>
		`);
	}


	$barcode_section.find('.barcode-input').on('keypress', function(e) {
		if (e.which !== 13) return;

		let scanned_value = $(this).val().trim();
		if (!scanned_value) return;

		if (scanned_orders[scanned_value]) {
			frappe.show_alert({
				message: __('Sales Order already scanned'),
				indicator: 'orange'
			});
			$(this).val('');
			return;
		}

		frappe.call({
			method: 'masar_miraaya_shipping.masar_miraaya_shipping.page.order_delivery.order_delivery.get_so_dispatch_details',
			args: {
				sales_orders: [scanned_value]
			},
			callback: function(r) {
				if (!r.message || r.message.length === 0) {
					frappe.show_alert({
						message: __('Only On the Way Orders are allowed'),
						indicator: 'red'
					});
					return;
				}

				let so = r.message[0];
				scanned_orders[so.sales_order] = so;
				render_scanned_list();
			}
		});

		$(this).val('');
	});

	// $orders_container.on('click', '.remove-so', function() {
	// 	let so = $(this).data('so');
	// 	delete scanned_orders[so];
	// 	render_scanned_list();
	// });

	$orders_container.on('click', '.assign-driver-btn', function() {
		let sales_orders = Object.keys(scanned_orders);

		if (sales_orders.length === 0) return;

		frappe.confirm(
			__('Set selected Sales Orders to Delivered'),
			function() {
				frappe.call({
					method: 'masar_miraaya_shipping.masar_miraaya_shipping.page.order_delivery.order_delivery.assign_driver_and_dispatch',
					args: {
						sales_orders: sales_orders
					},
					freeze: true,
					callback: function(r) {
						if (r.message && r.message.status === 'success') {
							frappe.msgprint({
								title: __('Success'),
								message: __(`${r.message.count} Sales Orders delivered successfully`),
								indicator: 'green'
							});
							scanned_orders = {};
							render_scanned_list();
						}
					}
				});
			}
		);
	});


	page.add_inner_button(__('Refresh'), function() {
		scanned_orders = {};
		render_scanned_list();
		$barcode_section.find('.barcode-input').val('').focus();
	});

	setInterval(() => {
		if (!$('.modal').is(':visible')) {
			$barcode_section.find('.barcode-input').focus();
		}
	}, 1000);
};
