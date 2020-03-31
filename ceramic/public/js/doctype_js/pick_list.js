frappe.ui.form.on('Pick List', {
	refresh: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
			frappe.call({
				method: "ceramic.api.check_counter_series",
				args: {
					'name': frm.doc.naming_series,
					'company_series': frm.doc.company_series,
				},
				callback: function(e) {
					frm.set_value("series_value", e.message);
				}
			});
		}
	},
	company: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	update_items: function(frm){
		frm.doc.locations = [];
		frm.doc.picked_sales_orders = [];
		frappe.call({
			method: 'ceramic.ceramic.doc_events.pick_list.get_item_from_sales_order',
			args: {
				company: frm.doc.company,
				item_code: frm.doc.item,
				customer: frm.doc.customer
			},
			callback: function(r){
				if (r.message){
					// console.log(r.message)
					r.message.forEach(function(item, index){
						if ((item.qty - item.picked_qty) <= 0.0){
							var d = frm.add_child('picked_sales_orders')
							frappe.model.set_value(d.doctype, d.name, 'qty', item.qty);
							frappe.model.set_value(d.doctype, d.name, 'uom', item.uom);
							frappe.model.set_value(d.doctype, d.name, 'stock_qty', item.stock_qty);
							frappe.model.set_value(d.doctype, d.name, 'conversion_factor', item.conversion_factor);
						} 
						else {
							var d = frm.add_child('locations')
							frappe.model.set_value(d.doctype, d.name, 'so_qty', item.qty)
							frappe.model.set_value(d.doctype, d.name, 'qty', item.qty - item.picked_qty);
						}
						frappe.model.set_value(d.doctype, d.name, 'customer', item.customer);
						frappe.model.set_value(d.doctype, d.name, 'warehouse', frm.doc.warehouse);
						frappe.model.set_value(d.doctype, d.name, 'date', item.delivery_date);
						frappe.model.set_value(d.doctype, d.name, 'item_code', item.item_code);
						frappe.model.set_value(d.doctype, d.name, 'item_name', item.item_name);
						frappe.model.set_value(d.doctype, d.name, 'picked_qty', item.picked_qty || 0);
						frappe.model.set_value(d.doctype, d.name, 'sales_order', item.sales_order);
						frappe.model.set_value(d.doctype, d.name, 'sales_order_item', item.sales_order_item);
						
					});
					frm.refresh();
				} else {
					frappe.throw(__("Please Select Item Code or Customer"))
				}
			}
		});
	},
	item: function(frm) {
		frm.trigger('get_item_qty')
	},
	customer: function(frm) {
		frm.trigger('get_item_qty')
	},
	get_item_qty: function(frm){
		frm.doc.available_qty = []
		frappe.call({
			method: 'ceramic.ceramic.doc_events.pick_list.get_item_qty',
			args: {
				company: frm.doc.company,
				item_code: frm.doc.item,
				customer: frm.doc.customer
			},
			callback: function(r){
				if (r.message){
					// console.log(r.message)
					r.message.forEach(function(item, index){
						let d = frm.add_child('available_qty')
						frappe.model.set_value(d.doctype, d.name, 'item_code', item.item_code);
						frappe.model.set_value(d.doctype, d.name, 'warehouse', item.warehouse);
						frappe.model.set_value(d.doctype, d.name, 'batch_no', item.batch_no);
						frappe.model.set_value(d.doctype, d.name, 'lot_no', item.lot_no);
						frappe.model.set_value(d.doctype, d.name, 'total_qty', item.total_qty);
						frappe.model.set_value(d.doctype, d.name, 'picked_qty', item.picked_qty);
						frappe.model.set_value(d.doctype, d.name, 'available_qty', item.available_qty);
						frappe.model.set_value(d.doctype, d.name, 'remaining', item.available_qty);
					});
					frm.refresh()
				} else {
					frappe.msgprint(__("Please Select Item Code or Customer"))
				}
				frm.refresh()
			}
		});
	},
	check_qty: function(frm){
		frm.doc.available_qty.forEach(function(item, index){
			let qty = 0;
			frm.doc.locations.forEach(function(value, key){
				if (value.item_code == item.item_code && value.batch_no == item.batch_no){
					qty += value.qty;
				}
			});
			let remaining_qty = item.available_qty - (qty || 0)
			frappe.model.set_value(item.doctype, item.name, 'picked_in_current', qty || 0);
			frappe.model.set_value(item.doctype, item.name, 'remaining', remaining_qty || 0);
			if (remaining_qty < 0){
				frappe.msgprint(__("ROW: " + item.idx + "The Reamaing Qty is less than zero in Lot No " + item.lot_no))	
			} 
		})
	},
	warehouse: function(frm){
		frm.doc.locations.forEach(function(item, index){
			frappe.model.set_value(item.doctype, item.name, 'warehouse', frm.doc.warehouse)
		});
	}
});

frappe.ui.form.on('Pick List Item', {
	qty: function(frm ,cdt, cdn){
		frm.events.check_qty(frm, cdt, cdn)
	},
	batch_no: function(frm ,cdt, cdn){
		frm.events.check_qty(frm, cdt, cdn)
	}
});

// let select_items = (args) => {
// 	frappe.require("assets/ceramic/js/utils/item_selector.js", function() {
// 		new ItemSelector(args)
// 	})
// }