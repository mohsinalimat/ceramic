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
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "MultiSelectList",
			"get_data": function (text) {
				//if (!frappe.query_report.item_group) return;
				return frappe.db.get_link_options('Item Group', text)
			},
			"change": function () {
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "tile_quality",
			"label": __("Tile Qulaity"),
			"fieldtype": "MultiSelectList",
			"get_data": function (text) {
				//if (!frappe.query_report.item_group) return;
				return frappe.db.get_link_options('Tile Quality', text)
			},
			"change": function () {
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "packing_type",
			"label": __("Packing Type"),
			"fieldtype": "MultiSelectList",
			"get_data": function (text) {
				//if (!frappe.query_report.item_group) return;
				return frappe.db.get_link_options('Packing Type', text)
			},
			"change": function () {
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "item_code",
			"label": __("Item Code"),
			"fieldtype": "MultiSelectList",
			"get_data": function (text) {
				//if (!frappe.query_report.item_group) return;
				return frappe.db.get_link_options('Item', text, filters = { 'is_item_series': 0, 'has_batch_no': 1 })
			},
			"change": function () {
				frappe.query_report.refresh();
			},

			// "get_query": function() {
			// 	var item_group = frappe.query_report.get_filter_value('item_group')
			// 	if (item_group){
			// 		return {
			// 			doctype: "Item",
			// 			filters: {
			// 				"item_group": item_group,
			// 				"is_item_series": 0
			// 			}
			// 		}
			// 	} else {
			// 		return {
			// 			doctype: "Item",
			// 			filters: {
			// 				"is_item_series": 0
			// 			}
			// 		}
			// 	}
			// }
		},
		{
			"fieldname": "not_in_item_code",
			"label": __("Not in Item Code"),
			"fieldtype": "MultiSelectList",
			"get_data": function (text) {
				//if (!frappe.query_report.item_group) return;
				return frappe.db.get_link_options('Item', text, filters = { 'is_item_series': 0, 'has_batch_no': 1 })
			},
			"change": function () {
				frappe.query_report.refresh();
			},
		},
		{
			"fieldname": "print_with_picked_qty",
			"label": __("Print With Picked Qty"),
			"fieldtype": "Check",
			"options": "Tile Quality",
		},
		{
			"fieldname": "sales_order",
			"label": __("Sales Order"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"get_query": function() {
				var company = frappe.query_report.get_filter_value('company');
				return {
					"doctype": "Sales Order",
					"filters": {
						"company": ['in', company],
						"docstatus": 1,
						"per_delivered": ['!=', 100],
						"status": ['not in', ('Draft', 'Submitted', 'Closed')]
					}
				}
			}
		},
		{
			"fieldname": "warehouse",
			"label": __("Show Warehouse"),
			"fieldtype": "Check"
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
		<table class="table table-bordered" style="margin: 0; font-size:80%;">
			<thead>
				<th>{{ __("Customer") }}</th>
				<th>{{ __("Rank") }}</th>
				<th>{{ __("Sales Order") }}</th>
				<th>{{ __("SO Date") }}</th>
				<th>{{ __("Pick List") }}</th>
				<th>{{ __("% Picked") }}</th>
				<th>{{ __("Picked") }}</th>
				<th>{{ __("Unpick Qty") }}</th>
				<th></th>
			</thead>
			<tbody>
				{% for (let row of data ) { %}
					<tr class="{{ __(row['pick_list_item']) }}">
						<td>{{ __(row['customer']) }}</td>
						<td>{{ __(row['order_rank']) }}</td>
						<td>{{ __(row['sales_order_link']) }}</td>
						<td>{{ __(row['date']) }}</td>
						<td>{{ __(row['pick_list_link']) }}</td>
						<td>{{ __(frappe.format(row['per_picked'], {'fieldtype': 'Percent'})) }}</td>
						<td>{{ __(row['picked_qty']) }}</td>
						<td><input type="float"  min="0" onkeypress="return (event.charCode == 8 || event.charCode == 0) ? null : event.charCode >= 48 && event.charCode <= 57" style="width:30px" id="{{ row['pick_list_item'] }}"></input></td>
						<td><button style="margin-left:5px;border:none;color: #fff; background-color: red; padding: 3px 5px;border-radius: 5px;" type="button" sales-order="{{ __(row['sales_order']) }}" sales-order-item="{{ __(row['sales_order_item']) }}" pick-list="{{ __(row['pick_list']) }}" pick-list-item="{{ __(row['pick_list_item']) }}" onClick=remove_picked_item_lot_wise(this.getAttribute("sales-order"),this.getAttribute("sales-order-item"),this.getAttribute("pick-list"),this.getAttribute("pick-list-item"),document.getElementById("{{ row['pick_list_item'] }}").value)>Unpick</button></td>
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
		callback: function (r) {
			let message = frappe.template.compile(template)({ 'data': r.message });
			frappe.msgprint({
				message: message,
				title: "Lot-Wise Balance Details : " + item_code,
				wide: true
			});
		}
	})
}

function remove_picked_item_lot_wise(sales_order, sales_order_item, pick_list, pick_list_item, unpick_qty) {
	frappe.call({
		method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
		args: {
			sales_order: sales_order,
			sales_order_item: sales_order_item,
			pick_list: pick_list,
			pick_list_item: pick_list_item,
			unpick_qty:unpick_qty
		},
		callback: function (r) {
			if(r.message){
				$(".modal").modal('hide');
				setTimeout(function(){frappe.msgprint(r.message)}, 500);
			}
			$('.' + pick_list_item).hide()
		}
	})
}

function new_qty_details(item_code,item_group, balance_qty, warehouse, buying_unit_price, batch_no, lot_no, packing_type) {
	let template = `
		<table class="table table-borderless" style="border: 0 !important; font-size:95%;">
			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><b>Item Group: </b> {{ data['item_group'] }}</td>
			</tr>
			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><b>Available Qty : </b>{{data['balance_qty']}}</td>
			<td style="border: 0 !important;"><b>Warehouse : </b>{{data['warehouse']}}</td>
			</tr>
			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><b>Batch : </b>{{data['batch_no']}}</td>
			<td style="border: 0 !important;"><b>Lot : </b>{{data['lot_no']}}</td>
			</tr>
			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><input type="float" style="width:50px" id="{{ 'new_qty' }}"></input>
			<td style="border: 0 !important;">
			<button style="margin-left:5px;border:0 !important;color: #fff; background-color: blue; padding: 3px 5px;border-radius: 5px;" type="button" warehouse = "{{ __(data['warehouse']) }}" balance_qty = "{{ __(data['balance_qty']) }}" item_code = "{{ __(data['item_code']) }}" buying_unit_price = "{{ __(data['buying_unit_price']) }}" batch_no = "{{ __(data['batch_no']) }}" lot_no = "{{ __(data['lot_no']) }}" packing_type = "{{ __(data['packing_type']) }}" onClick=create_stock_entry(this.getAttribute("warehouse"),this.getAttribute("item_code"),this.getAttribute("balance_qty"),this.getAttribute("buying_unit_price"),document.getElementById("{{ 'new_qty' }}").value,this.getAttribute("batch_no"),this.getAttribute("lot_no"),this.getAttribute("packing_type"))>Create Stock Entry</button>
			</tr>
		</table>`;
		let message = frappe.template.compile(template)({ 'data': {"item_code":item_code,"item_group":item_group,"balance_qty":balance_qty,"warehouse":warehouse,"buying_unit_price":buying_unit_price,"batch_no":batch_no, "lot_no":lot_no, "packing_type":packing_type} });
		frappe.msgprint({
			message: message,
			title: "Item Code : " + item_code,
			wide: true,
		});
}

function create_stock_entry(warehouse,item_code,balance_qty,buying_unit_price,new_qty,batch_no,lot_no,packing_type) {
	if ((new_qty) < 0){
		frappe.throw("Please Don't Enter Negative Qty")
	}

	$(".modal").modal('hide');
	frappe.call({
		method:"ceramic.ceramic.report.lot_wise_balance.lot_wise_balance.create_stock_entry",
		args:
		{
			warehouse:warehouse,
			item_code:item_code,
			balance_qty:balance_qty,
			buying_unit_price:buying_unit_price,
			new_qty:new_qty,
			batch_no:batch_no,
			lot_no:lot_no,
			packing_type:packing_type
		},
		freeze: true,
		freeze_message: "<b>creating stock entry...<b>",
		callback:function(r){
			frappe.msgprint(r.message)
			//setTimeout(function () {frappe.msgprint(r.message)}, 1000)
			// window.location.reload();
			//setTimeout(function () {$(".modal").modal('hide');}, 1000)	 
		}
	})
}