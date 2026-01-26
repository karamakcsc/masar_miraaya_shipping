frappe.pages['packing'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Packing Process',
		single_column: true
	});

	// main container
	let $container = $('<div class="packing-container"></div>').appendTo(page.main);
	
	// barcode input field
	let $barcode_section = $(`
		<div class="barcode-scanner" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;">
			<h4>Scan Barcode</h4>
			<input type="text" class="form-control barcode-input" placeholder="Scan or enter Sales Order ID or Magento ID..." autofocus>
		</div>
	`).appendTo($container);

	// sales orders list container
	let $orders_container = $('<div class="sales-orders-list"></div>').appendTo($container);

	// render sales orders with barcodes
	function render_orders(order) {
		$orders_container.empty();
		
		if (!order) {
			$orders_container.append('<p style="text-align: center; padding: 20px;">No confirmed sales orders found.</p>');
			return;
		}

		frappe.call({
			method: 'masar_miraaya_shipping.masar_miraaya_shipping.page.packing.packing.get_confirmed_sales_orders',
			args: {
				so: order
			},
			callback: function(r) {
				if (r.message) {
					let $table = $(`
						<table class="table table-bordered" style="margin-top: 20px;">
							<thead>
								<tr>
									<th>Sales Order</th>
									<th>Magento ID</th>
									<th>Customer</th>
									<th>Date</th>
									<th>Total Qty</th>
									<th>Amount</th>
									<th>Barcode</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody></tbody>
						</table>
					`);

					let $tbody = $table.find('tbody');
					if (r.message.length === 0) {
						$tbody.append('<tr><td colspan="8" style="text-align: center;">No sales orders found.</td></tr>');
					}
					r.message.forEach(r => {
						let $row = $(`
							<tr>
								<td><a href="/app/sales-order/${r.name}">${r.name}</a></td>
								<td>${r.custom_magento_id || '-'}</td>
								<td>${r.customer_name}</td>
								<td>${frappe.datetime.str_to_user(r.transaction_date)}</td>
								<td style="text-align: center";>${r.total_qty}</td>
								<td>${format_currency(r.grand_total)}</td>
								<td>
									<svg class="barcode-${r.name.replace(/[^a-zA-Z0-9]/g, '')}"></svg>
								</td>
								<td>
									<button class="btn btn-sm btn-primary open-pick-list" data-order="${r.name}">
										Open Pick List
									</button>
								</td>
							</tr>
						`);

						$tbody.append($row);

						// Generate barcode using JsBarcode
						setTimeout(() => {
							try {
								JsBarcode(`.barcode-${r.name.replace(/[^a-zA-Z0-9]/g, '')}`, r.name, {
									format: "CODE128",
									width: 1,
									height: 40,
									displayValue: true,
									fontSize: 12
								});
							} catch (e) {
								console.error('Barcode generation failed:', e);
							}
						}, 100);
					})
					$orders_container.append($table);
				}
			}
		});
	}

	function open_pick_list(sales_order) {
		frappe.call({
			method: 'masar_miraaya_shipping.masar_miraaya_shipping.page.packing.packing.get_picklist_from_so',
			args: {
				so: sales_order
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					frappe.open_in_new_tab = true;
					frappe.set_route('Form', 'Pick List', r.message);
				} else if (r.message && !r.message.success) {
					frappe.msgprint({
						message: __(r.message.message),
						indicator: 'orange'
					});
				} else {
					frappe.msgprint({
						title: __('No Pick List Found'),
						message: __('No Pick List is connected to the ID'),
						indicator: 'orange'
					});
				}
			}
		});
	}

	// barcode scan
	$barcode_section.find('.barcode-input').on('keypress', function(e) {
		if (e.which === 13) { // Enter key
			let scanned_value = $(this).val().trim();
			if (scanned_value) {
				render_orders(scanned_value);
				open_pick_list(scanned_value);
				$(this).val('');
			}
		}
	});

	// open pick list button
	$orders_container.on('click', '.open-pick-list', function() {
		let sales_order = $(this).data('order');
		open_pick_list(sales_order);
	});

	// refresh button
	page.add_inner_button(__('Refresh'), function() {
		$orders_container.empty();
		$barcode_section.find('.barcode-input').val('').focus();
	});

	// JsBarcode
	if (typeof JsBarcode === 'undefined') {
		frappe.require('https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js', function() {
			console.log('JsBarcode loaded successfully');
		});
	}

	// auto focus barcode
	setInterval(function() {
		if (!$('.modal').is(':visible')) {
			$barcode_section.find('.barcode-input').focus();
		}
	}, 1000);
}