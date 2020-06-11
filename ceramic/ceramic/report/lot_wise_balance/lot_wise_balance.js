// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Lot-Wise Balance"] = {
	"filters": [
				{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": "80",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "MultiSelectList",
			"get_data": function(text){
				//if (!frappe.query_report.item_group) return;
				return frappe.db.get_link_options('Item Group',text)
			},
			"change": function(){
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname":"tile_quality",
			"label": __("Tile Qulaity"),
			"fieldtype": "Link",
			"options": "Tile Quality",
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			get_query: function() {
				var item_group = frappe.query_report.get_filter_value('item_group')
				if (item_group){
					return {
						doctype: "Item",
						filters: {
							"item_group": item_group,
							"is_item_series": 0
						}
					}
				} else {
					return {
						doctype: "Item",
						filters: {
							"is_item_series": 0
						}
					}
				}
			}
		},
		{
			"fieldname":"print_with_picked_qty",
			"label": __("Print With Picked Qty"),
			"fieldtype": "Check",
			"options": "Tile Quality",
		},
	]
}


function get_picked_item_details(item_code, batch_no, company, from_date, to_date, bal_qty, total_picked_qty, total_remaining_qty, lot_no) {
	let template = `
		<table class="table table-borderless" style="border: 0 !important; font-size:95%;">
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
		<table class="table table-bordered" style="margin: 0; font-size:90%;">
			<thead>
				<th>{{ __("Customer") }}</th>
				<th>{{ __("Sales Order") }}</th>
				<th>{{ __("SO Date") }}</th>
				<th>{{ __("Picked") }}</th>
				<th>{{ __("Unpick") }}</th>
			</thead>
			<tbody>
				{% for (let row of data ) { %}
					<tr class="{{ __(row['pick_list_item']) }}">
						<td>{{ __(row['customer']) }}</td>
						<td>{{ __(row['sales_order_link']) }}</td>
						<td>{{ __(row['date']) }}</td>
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
				title: "Lot-Wise Balance Details : " + item_code,
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

