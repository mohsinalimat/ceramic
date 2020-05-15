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
function get_picked_item_details(item_code, batch_no, company, from_date, to_date) {
	let template = `
		<h3 style="text-align: center">{{ data[0]['item_name'] }}</h3>
		<table class="table table-bordered" style="margin: 0;">
			<thead>
				<th>{{ __("Customer") }}</th>
				<th>{{ __("Sales Order") }}</th>
				<th>{{ __("Picked Qty") }}</th>
				<th>{{ __("Delivered Qty") }}</th>
				<th>{{ __("Remaining Qty") }}</th>
			</thead>
			<tbody>
				{% for (let row of data ) { %}
					<tr>
						<td>{{ __(row['customer']) }}</td>
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
		method: "ceramic.api.get_picked_item",
		args: {
			item_code: item_code,
			batch_no: batch_no,
			from_date: from_date,
			to_date: to_date,
			company: company
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