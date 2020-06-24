frappe.ui.form.on('Pick List', {
	before_validate: (frm) => {
		frm.trigger('check_qty')
	},
	setup: (frm) => {
		frm.clear_custom_buttons()
		frm.custom_make_buttons = {
			'Delivery Note': 'Delivery Note',
			'Stock Entry': 'Stock Entry',
		};
		frm.set_query('warehouse', (doc) => {
			if (!frm.doc.company) {
				frappe.msgprint(__("Please select Item Code"));
			}
			else {
				return {
					filters: {
						'company': frm.doc.company
					}
				}
			}
		});
		frm.set_query("batch_no", "locations", function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			if (!d.item_code) {
				frappe.msgprint(__("Please select Item Code"));
			}
			else {
				return {
					query: "ceramic.query.get_batch_no",
					filters: {
						'item_code': d.item_code,
						'company': frm.doc.company
					}
				}
			}
		});
		frm.set_query("sales_order", function () {
			return {
				query: "ceramic.api.sales_order_query",
				filters: {
					"customer": frm.doc.customer,
					"item_code": frm.doc.item,
					'company': frm.doc.company
				}
			}
		});
		frm.clear_custom_buttons()
	},
	refresh: function(frm) {
		frm.clear_custom_buttons()
		if (frm.doc.__islocal){
			if ((frm.doc.customer || frm.doc.item) && frm.doc.available_qty.length == 0) {
				frm.trigger('get_item_qty');
				frm.trigger('get_picked_items');
			}
			frm.trigger('naming_series');
		}
		frm.set_df_property("locations", "read_only", frm.doc.docstatus == 0 ? 0 : 1);
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
	},
	add_get_items_button: (frm) => {
		frm.remove_custom_button(__('Get Items'));
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
			frappe.call({
				method: "ceramic.api.check_counter_series",
				args: {
					'name': frm.doc.naming_series,
					'company_series': frm.doc.company_series,
					'date': cur_frm.doc.transaction_date
				},
				callback: function(e) {
					if (e.message){
						frm.set_value("series_value", e.message);
					}
				}
			});
		}
	},
	update_items: function(frm){
		frm.trigger('get_locations')
	},
	get_picked_items: (frm) => {
		frm.doc.picked_sales_orders = []
		frappe.call({
			method: 'ceramic.ceramic.doc_events.pick_list.get_picked_items',
			args: {
				company: frm.doc.company,
				item_code: frm.doc.item,
				customer: frm.doc.customer,
				sales_order: frm.doc.sales_order,
			},
			callback: function(r){
				if (r.message){
					r.message.forEach(function(item, index){
						var d = frm.add_child('picked_sales_orders')
						frappe.model.set_value(d.doctype, d.name, 'customer', item.customer);
						frappe.model.set_value(d.doctype, d.name, 'batch_no', item.batch_no);
						frappe.model.set_value(d.doctype, d.name, 'lot_no', item.lot_no);
						frappe.model.set_value(d.doctype, d.name, 'item_code', item.item_code);
						frappe.model.set_value(d.doctype, d.name, 'so_qty', item.so_qty);
						frappe.model.set_value(d.doctype, d.name, 'uom', item.uom);
						frappe.model.set_value(d.doctype, d.name, 'stock_qty', item.stock_qty);
						frappe.model.set_value(d.doctype, d.name, 'stock_uom', item.stock_uom);
						frappe.model.set_value(d.doctype, d.name, 'conversion_factor', item.conversion_factor);
						frappe.model.set_value(d.doctype, d.name, 'picked_qty', item.qty);
						frappe.model.set_value(d.doctype, d.name, 'item_name', item.item_name);
						frappe.model.set_value(d.doctype, d.name, 'pick_list', item.parent);
						frappe.model.set_value(d.doctype, d.name, 'pick_list_item', item.name);
						frappe.model.set_value(d.doctype, d.name, 'sales_order', item.sales_order);
						frappe.model.set_value(d.doctype, d.name, 'sales_order_item', item.sales_order_item);
						frappe.model.set_value(d.doctype, d.name, 'date', item.date);
						frappe.model.set_value(d.doctype, d.name, 'so_picked_percent', item.per_picked);
					});
					frm.refresh_field('picked_sales_orders');
				} else {
					frappe.msgprint({
						"title": "Error",
						"message": "Please Select Item Code or Customer",
						"indicator": "red" //or blue, orange, green
					});
				}
			}
		});
	},
	get_locations: (frm) => {
		frm.doc.locations = [];

		frappe.call({
			method: 'ceramic.ceramic.doc_events.pick_list.get_item_from_sales_order',
			args: {
				company: frm.doc.company,
				item_code: frm.doc.item,
				customer: frm.doc.customer,
				sales_order: frm.doc.sales_order
			},
			callback: function(r){
				if (r.message){
					r.message.forEach(function(item, index){
						if ((item.qty - item.picked_qty) > 0.0){
							var d = frm.add_child('locations')
							frappe.model.set_value(d.doctype, d.name, 'so_qty', item.qty)
							frappe.model.set_value(d.doctype, d.name, 'qty', item.qty);
							frappe.model.set_value(d.doctype, d.name, 'customer', item.customer);
							frappe.model.set_value(d.doctype, d.name, 'date', item.transaction_date);
							frappe.model.set_value(d.doctype, d.name, 'delivery_date', item.delivery_date);
							frappe.model.set_value(d.doctype, d.name, 'item_code', item.item_code);
							frappe.model.set_value(d.doctype, d.name, 'item_name', item.item_name);
							frappe.model.set_value(d.doctype, d.name, 'picked_qty', item.picked_qty || 0);
							frappe.model.set_value(d.doctype, d.name, 'sales_order', item.sales_order);
							frappe.model.set_value(d.doctype, d.name, 'sales_order_item', item.sales_order_item);
							frappe.model.set_value(d.doctype, d.name, 'so_real_qty', item.real_qty);
							frappe.model.set_value(d.doctype, d.name, 'packing_type', item.packing_type);
							frappe.model.set_value(d.doctype, d.name, 'so_picked_percent', item.per_picked);
						}
					});
					frm.refresh_field('locations');
				} else {
					frappe.msgprint({
						"title": "Error",
						"message": "Please Select Item Code or Customer",
						"indicator": "red" //or blue, orange, green
					});
				}
			}
		});
	},
	item: function(frm) {
		frm.trigger('get_item_qty')
		frm.trigger('get_picked_items')
	},
	customer: function(frm) {
		frm.trigger('get_item_qty')
		frm.trigger('get_picked_items')
	},
	sales_order: function(frm) {
		frm.trigger('get_item_qty')
		frm.trigger('get_picked_items')
	},
	get_item_qty: function(frm){
		frm.doc.available_qty = []
		frappe.call({
			method: 'ceramic.ceramic.doc_events.pick_list.get_item_qty',
			args: {
				company: frm.doc.company,
				item_code: frm.doc.item,
				customer: frm.doc.customer,
				sales_order: frm.doc.sales_order
			},
			callback: function(r){
				if (r.message){
					r.message.forEach(function(item, index){
						let d = frm.add_child('available_qty')
						frappe.model.set_value(d.doctype, d.name, 'item_code', item.item_code);
						frappe.model.set_value(d.doctype, d.name, 'batch_no', item.batch_no);
						frappe.model.set_value(d.doctype, d.name, 'lot_no', item.lot_no);
						frappe.model.set_value(d.doctype, d.name, 'total_qty', item.total_qty);
						frappe.model.set_value(d.doctype, d.name, 'picked_qty', item.picked_qty);
						frappe.model.set_value(d.doctype, d.name, 'available_qty', item.available_qty);
						frappe.model.set_value(d.doctype, d.name, 'remaining', item.available_qty);
					});
					
				} else {
					frappe.msgprint({
						"title": "Error",
						"message": "Please Select Item Code or Customer",
						"indicator": "red" //or blue, orange, green
					});
				}
				frm.refresh_field('available_qty')
			}
		});
	},
	check_qty: function(frm, cdt, cdn){
		
		frm.doc.available_qty.forEach(function(item, index){
			let qty = 0;
			(frm.doc.locations || []).forEach(function(value, key){
				if (value.item_code == item.item_code && value.batch_no == item.batch_no){
					qty += value.qty;
				}
			});
			let remaining_qty = item.available_qty - (qty || 0)
			frappe.model.set_value(item.doctype, item.name, 'picked_in_current', qty || 0);
			frappe.model.set_value(item.doctype, item.name, 'remaining', remaining_qty || 0);
			if (remaining_qty < 0){
				let d = locals[cdt][cdn]
				frappe.model.set_value(cdt, cdn, 'qty', d.qty + remaining_qty)
			} 
		})
	},
	company: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
});

frappe.ui.form.on('Pick List Item', {
	qty: function(frm ,cdt, cdn){
		let d = locals[cdt][cdn];
		let sales_order_item = d.sales_order_item;
		frm.events.check_qty(frm, cdt, cdn)
		let remaining_qty = 0;
		let qty = 0;
		frm.doc.locations.forEach(function(item, idx){
			if (item.sales_order_item === sales_order_item){
				qty = qty + item.qty
				frappe.model.set_value(item.doctype, item.name, 'remaining_qty', d.so_qty - d.picked_qty - qty)
			}
		});
		frm.refresh_field('locations');
	},
	batch_no: function(frm ,cdt, cdn){
		let d = locals[cdt][cdn];
		frm.events.check_qty(frm, cdt, cdn);
	},
	update_item: function(frm, cdt, cdn){
		let d = locals[cdt][cdn];
		select_items({frm:frm, item_code: d.item_code, sales_order: d.sales_order, sales_order_item: d.sales_order_item, so_qty: d.so_qty, company: frm.doc.company, customer: d.customer, date: d.date, delivery_date: d.delivery_date, picked_qty: d.picked_qty, so_real_qty: d.so_real_qty, remaining_to_pick: (d.so_qty - d.picked_qty), batch_no: d.batch_no, qty: d.qty, packaging_type: d.packing_type, date: d.date, so_picked_percent: d.so_picked_percent, idx: d.idx});
	},
});

const select_items = (args) => {
	frappe.require("assets/ceramic/js/utils/item_selector.js", function() {
		new ItemSelector(args)
	})
}

frappe.ui.form.on('Picked Sales Orders', {
	'unpick_item': (frm, cdt, cdn) => {
		let d = locals[cdt][cdn]

		frappe.call({
			method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
			args: {
				'sales_order': d.sales_order,
				'sales_order_item': d.sales_order_item,
				'pick_list': d.pick_list,
				'pick_list_item': d.pick_list_item,
				'unpick_qty': d.unpick_qty || 0
			},
			callback: function(r){
				frm.events.get_item_qty(frm);
				frm.events.get_picked_items(frm);
			}
		})
	}
});

frappe.ui.keys.add_shortcut({
	shortcut: 'ctrl+i',
    action: function(e) { 
		e.preventDefault();	
		if (!cur_dialog){
			const current_doc = $('.data-row.editable-row').parent().attr("data-name");
			const d = locals["Pick List Item"][current_doc];
			select_items({
				frm:cur_frm,
				item_code: d.item_code,
				sales_order: d.sales_order,
				sales_order_item: d.sales_order_item,
				so_qty: d.so_qty,
				company: cur_frm.doc.company,
				customer: d.customer,
				date: d.date, delivery_date:
				d.delivery_date,
				picked_qty: d.picked_qty,
				so_real_qty: d.so_real_qty,
				remaining_to_pick: (d.so_qty - d.picked_qty),
				batch_no: d.batch_no,
				qty: d.qty,
				packaging_type: d.packing_type,
				date: d.date,
				so_picked_percent: d.so_picked_percent,
				idx: d.idx
			});
		}
	},
	page: this.page,
    description: __('Select Lot from warehouse'),
    ignore_inputs: true,
});

frappe.ui.keys.add_shortcut({
	shortcut: 'ctrl+d',
    action: function(e){ 
		e.preventDefault();

		if (cur_dialog){	
		
			// const current_doc = $('.data-row.editable-row').parent().attr("data-name");
			// var d = locals["Pick List Item"][current_doc];
			let next = cint(cur_dialog.fields_dict.idx.value) + 1
			let next_locations = cur_frm.doc.locations[next - 1]
			if (next_locations){
				// cur_frm.get_field('items').grid.get_field("item_code").'$input'.focus()
				cur_dialog.cancel();
				var d = locals[next_locations.doctype][next_locations.name];
				select_items({
					frm:cur_frm,
					item_code: d.item_code,
					sales_order: d.sales_order,
					sales_order_item: d.sales_order_item,
					so_qty: d.so_qty,
					company: cur_frm.doc.company,
					customer: d.customer,
					date: d.date, delivery_date:
					d.delivery_date,
					picked_qty: d.picked_qty,
					so_real_qty: d.so_real_qty,
					remaining_to_pick: (d.so_qty - d.picked_qty),
					batch_no: d.batch_no,
					qty: d.qty,
					packaging_type: d.packing_type,
					date: d.date,
					so_picked_percent: d.so_picked_percent,
					idx: d.idx
				});
			}
		}
	},
	page: this.page,
    description: __('Select Lot from warehouse'),
    ignore_inputs: true,
});

frappe.ui.keys.add_shortcut({
	shortcut: 'ctrl+u',
    action: function(e){ 
		e.preventDefault();

		if (cur_dialog){	
		
			// const current_doc = $('.data-row.editable-row').parent().attr("data-name");
			// var d = locals["Pick List Item"][current_doc];
			let previous = cint(cur_dialog.fields_dict.idx.value) - 1
			let previous_locations = cur_frm.doc.locations[previous - 1]
			if (previous_locations){
				// cur_frm.get_field('items').grid.get_field("item_code").'$input'.focus()
				cur_dialog.cancel();
				var d = locals[previous_locations.doctype][previous_locations.name];
				select_items({
					frm:cur_frm,
					item_code: d.item_code,
					sales_order: d.sales_order,
					sales_order_item: d.sales_order_item,
					so_qty: d.so_qty,
					company: cur_frm.doc.company,
					customer: d.customer,
					date: d.date, delivery_date:
					d.delivery_date,
					picked_qty: d.picked_qty,
					so_real_qty: d.so_real_qty,
					remaining_to_pick: (d.so_qty - d.picked_qty),
					batch_no: d.batch_no,
					qty: d.qty,
					packaging_type: d.packing_type,
					date: d.date,
					so_picked_percent: d.so_picked_percent,
					idx: d.idx
				});
			}
		}
	},
	page: this.page,
    description: __('Select Lot from warehouse'),
    ignore_inputs: true,
});