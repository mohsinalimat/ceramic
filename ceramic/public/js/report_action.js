function get_lot_wise_item_details(item_code, company, from_date, to_date) {
	let template = `
		<h3 style="text-align: center">{{ data[0]['item_name'] }}</h3>
		<table class="table table-bordered" style="margin: 0;">
			<thead>
				<th>{{ __("Lot No") }}</th>
				<th>{{ __("Warehouse") }}</th>
				<th>{{ __("Balance Qty") }}</th>
				<th>{{ __("Picked Qty") }}</th>
				<th>{{ __("Remaining Qty") }}</th>
			</thead>
			<tbody>
				{% for (let row of data ) { %}
					<tr>
						<td>{{ __(row['lot_no']) }}</td>
						<td>{{ __(row['warehouse']) }}</td>
						<td>{{ __(row['bal_qty']) }}</td>
						<td>{{ __(row['picked_qty']) }}</td>
						<td>{{ __(row['remaining_qty']) }}</td>
					</tr>
				{% } %}
			</tbody>
		</table>`;
		
		// docudocument.getElementById("demo").innerHTML = item_code;

		frappe.call({
		method: "ceramic.api.get_lot_wise_data",
		args: {
			item_code: item_code,
			company: company,
			from_date: from_date,
			to_date: to_date
		},
		callback: function(r){
			let message = frappe.template.compile(template)({'data': r.message});
			frappe.msgprint({
				message: message, 
				title: "Lot-Wise Detail",
				wide: true,
			});
		}
	})
}
function get_picked_item_details(item_code, batch_no, company, from_date, to_date, bal_qty, total_picked_qty, total_remaining_qty, lot_no) {4
	let template = `
		<h3 style="text-align: center">{{ data[0]['item_name'] }}</h3>
		<table class="table table-borderless" style="border: 0 !important;">
			<tr style="border: 0 !important;">
				<td style="border: 0 !important;"><b>Lot No: </b> {{ data[0]['lot_no'] }}</td>
				<td style="border: 0 !important;"><b>Picked Qty: </b> {{ data[0]['total_picked_qty'] }}</td>
			</tr>
			<tr style="border: 0 !important;">
				<td style="border: 0 !important;"><b>Qty: </b> {{ data[0]['bal_qty'] }}</td>
				<td style="border: 0 !important;"><b>Available Qty: </b> {{ data[0]['total_remaining_qty'] }}</td>
			</tr>
		</table>
		{% if data[0]['customer'] %}
		<table class="table table-bordered" style="margin: 0;">
			<thead>
				<th>{{ __("Customer") }}</th>
				<th>{{ __("Sales Order") }}</th>
				<th>{{ __("Picked") }}</th>
				<th>{{ __("Unpick") }}</th>
			</thead>
			<tbody>
				{% for (let row of data ) { %}
					<tr class="{{ __(row['pick_list_item']) }}">
						<td>{{ __(row['customer']) }}</td>
						<td>{{ __(row['sales_order_link']) }}</td>
						<td>{{ __(row['picked_qty']) }}</td>
						<td><button style="margin-left:5px;border:none;color: #fff; background-color: red; padding: 3px 5px;border-radius: 5px;" type="button" sales-order="{{ __(row['sales_order']) }}" sales-order-item="{{ __(row['sales_order_item']) }}" pick-list="{{ __(row['pick_list']) }}" pick-list-item="{{ __(row['pick_list_item']) }}" onClick=remove_picked_item_lot_wise(this.getAttribute("sales-order"),this.getAttribute("sales-order-item"),this.getAttribute("pick-list"),this.getAttribute("pick-list-item"))>Unpick</button></td>
					</tr>
				{% } %}
			</tbody>
		</table>
		{% endif %}`;
		
		// docudocument.getElementById("demo").innerHTML = item_code;

		frappe.call({
		method: "ceramic.api.get_picked_item",
		args: {
			item_code: item_code,
			batch_no: batch_no,
			from_date: from_date,
			to_date: to_date,
			company: company,
			bal_qty: bal_qty, 
			total_picked_qty: total_picked_qty, 
			total_remaining_qty: total_remaining_qty,
			lot_no: lot_no
		},
		callback: function(r){
			let message = frappe.template.compile(template)({'data': r.message});
			frappe.msgprint({
				message: message, 
				title: "Lot-Wise Detail",
				wide: true,
			});
		}
	})
}

function remove_picked_item_lot_wise(sales_order, sales_order_item, pick_list, pick_list_item) {
	frappe.call({
		method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
		args: {
			sales_order: sales_order,
			sales_order_item: sales_order_item,
			pick_list: pick_list,
			pick_list_item: pick_list_item
		},
		callback: function(r){
			$('.' + pick_list_item).hide()
		}
	})
}