cur_frm.fields_dict.from_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.to_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("s_warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("t_warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
		}
	}
};


this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
	this.frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (!d.item_code) {
			frappe.msgprint(__("Please select Item Code"));
		}
		else if (!d.s_warehouse) {
			frappe.msgprint(__("Please select source warehouse"));
		}
		else {
			return {
				query: "ceramic.query.get_batch_no",
				filters: {
					'item_code': d.item_code,
					'warehouse': d.s_warehouse
				}
			}
		}
	});
	// this.frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
	// 	let d = locals[cdt][cdn];
	// 	if (!d.item_code) {
	// 		frappe.throw(__("Please enter Item Code to get batch no"));
	// 	}
	// 	else {
	// 		return {
	// 			query: "ceramic.controllers.queries.get_batch_no",
	// 			filters: {
	// 				'item_code': d.item_code,
	// 				'warehouse': d.warehouse
	// 			}
	// 		}
	// 	}
	// });
}
frappe.ui.form.on('Stock Entry', {
	refresh: function (frm) {
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
	},
	validate: function (frm) {
		frm.trigger('calculate_totals')
	},
	calculate_totals: function (frm) {
		let premium_qty = 0.0
		let golden_qty = 0.0
		let classic_qty = 0.0
		let economy_qty = 0.0
		let total_qty = 0.0

		frm.doc.items.forEach(function (d) {
			total_qty += d.qty
			if (d.tile_quality == "Premium") {
				premium_qty += d.qty
			}
			if (d.tile_quality == "Golden") {
				golden_qty += d.qty
			}
			if (d.tile_quality == "Classic") {
				classic_qty += d.qty
			}
			if (d.tile_quality == "Economy") {
				economy_qty += d.qty
			}
		});
		frm.set_value("premium_qty", premium_qty)
		frm.set_value("golden_qty", golden_qty)
		frm.set_value("classic_qty", classic_qty)
		frm.set_value("economy_qty", economy_qty)
		frm.set_value("total_qty", total_qty)
		frm.set_value('premium_percentage', flt(premium_qty / total_qty * 100))
	},
	setup: function (frm) {
		frm.set_query("finish_item", function () {
			return {
				filters: {
					"tile_quality": "Premium",
					"is_stock_item": 1,
				}
			}
		});
	},
	
	update_items: function (frm) {
		if (frm.doc.docstatus == 0) {
			if (!frm.doc.items) {
				frm.doc.items = []
			}
			if (!frm.doc.finish_item) {
				frm.doc.finish_item = []
			}
			var finish_item_list = [];
			var item_list = [];
			var categories = ['-I-', '-II-', '-III-', '-IV-'];
			var i = 0;
			var new_item_list = [];
        
			for (i = 0; i < frm.doc.finish_item.length; i++) {
				finish_item_list.push(frm.doc.finish_item[i].item_detail)
			}
		
			for (i = 0; i < frm.doc.items.length; i++) {
				item_list.push(frm.doc.items[i].item_code)
			}

			if (item_list.length == 1) {
				if (!frm.doc.items[0].item_code) {
					item_list = [];
					frm.doc.items = [];
				}
			}
        
			if (finish_item_list.length > 0) {
				if (item_list.length > 0) {
					for (i = 0; i < frm.doc.items.length; i++) {
						var item = frm.doc.items[i].item_code.replace('-IV-', '-I-');
						item = item.replace('-III-', '-I-');
						item = item.replace('-II-', '-I-');
						item = item.replace('-I-', '-I-');
						if (finish_item_list.includes(item)) {
							new_item_list.push(frm.doc.items[i]);
						}
					}
				
					frm.doc.items = new_item_list;
					for (i = 0; i < frm.doc.finish_item.length; i++) {
						var count = 0;
						var finish_item = frm.doc.finish_item[i].item_detail;

						for (var j = 0; j < frm.doc.items.length; j++) {
							var item = frm.doc.items[j].item_code;
							if (finish_item == item) {
								count++;
							}
						}

						if (count === 0) {
							for (var j = 0; j < categories.length; j++) {
								var new_name = finish_item.replace('-I-', categories[j]);
								let item_row = frappe.model.add_child(frm.doc, 'Stock Entry Detail', 'items');
								item_row.item_code = new_name;
								// frappe.model.set_value(item_row.doctype, item_row.name, 'item_code', new_name);
								frappe.model.set_value(item_row.doctype, item_row.name, 'qty', 0);
								get_item_details(new_name).then(data => {
									frappe.model.set_value(item_row.doctype, item_row.name, 'item_name', data.name);
									frappe.model.set_value(item_row.doctype, item_row.name, 'uom', data.stock_uom);
									frappe.model.set_value(item_row.doctype, item_row.name, 'stock_uom', data.stock_uom);
									frappe.model.set_value(item_row.doctype, item_row.name, 't_warehouse', frm.doc.to_warehouse);
								});
							
							}
						}
					}
					frm.refresh_field('items');
				} else {
					frm.doc.finish_item.forEach(function (originial_item, index) {
						categories.forEach(function (item, index) {
						
							var new_name = originial_item["item_detail"].replace('-I-', item);
						
							let item_row = frappe.model.add_child(frm.doc, 'Stock Entry Detail', 'items');
							item_row.item_code = new_name;

							// frappe.model.set_value(item_row.doctype, item_row.name, 'item_code', new_name);
							frappe.model.set_value(item_row.doctype, item_row.name, 'qty', 0);
							get_item_details(new_name).then(data => {
								frappe.model.set_value(item_row.doctype, item_row.name, 'item_name', data.name);
								frappe.model.set_value(item_row.doctype, item_row.name, 'uom', data.stock_uom);
								frappe.model.set_value(item_row.doctype, item_row.name, 'stock_uom', data.stock_uom);
								frappe.model.set_value(item_row.doctype, item_row.name, 't_warehouse', frm.doc.to_warehouse);
							});
						
						});
					});
					frm.refresh_field('items');
				}
			} else {
				frm.doc.items = [];
			}

			for (i = 0; i < frm.doc.items.length; i++) {
				frm.doc.items[i].idx = i + 1;
			}
		}
		frm.doc.items.forEach(function (d) {
			frappe.call({
				method: 'ceramic.ceramic.doc_events.stock_entry.get_product_price',
				args: {
					'item_code': d.item_code,
					'item_group': d.item_group
				},
				callback: function (r) {
					if (r.message) {

						frappe.model.set_value(d.doctype, d.name, 'basic_rate', r.message);
						frappe.model.set_value(d.doctype, d.name, 'valuation_rate', r.message);
					}
					if (r.error) {
						frappe.throw({
							title: __('Item Price not found'),
							message: r.error
						});
					}

				}
			});
		})
		frm.refresh_field('items');
	},
	before_validate2: function (frm) {
		console.log("Before Validate get price");
		frm.doc.items.forEach(function (d) { 
			frappe.call({
				method: 'ceramic.ceramic.doc_events.stock_entry.get_product_price',
				args: {
					'doc': frm.doc
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(d.doctype, d.name, 'basic_rate', r.message);
						frappe.model.set_value(d.doctype, d.name, 'valuation_rate', r.message);
					}
					if (r.error) {
						frappe.throw({
							title: __('Item Price not found'),
							message: r.error
						});
					}

				}

			})
		});
	}

});

function get_item_details(item_code) {
	if (item_code) {
		return frappe.xcall('erpnext.stock.doctype.pick_list.pick_list.get_item_details', {
			item_code
		})
	}
}

frappe.ui.form.on('Stock Entry Detail', {
	duplicate: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		let m = frm.add_child("items");
		frappe.model.set_value(m.doctype, m.name, 's_warehouse', d.s_warehouse);
		frappe.model.set_value(m.doctype, m.name, 's_warehouse', d.s_warehouse);
		frappe.model.set_value(m.doctype, m.name, 'item_code', d.item_code);
		frappe.model.set_value(m.doctype, m.name, 'packing_type', d.packing_type);
		frappe.model.set_value(m.doctype, m.name, 'lot_no', d.lot_no);
		frappe.model.set_value(m.doctype, m.name, 'rate', d.rate);
		
		frm.refresh();
	},
	qty: function (frm, cdt, cdn) {
		frm.events.calculate_totals(frm)

		var d = locals[cdt][cdn];
		if (d.item_code) {
			var args = {
				'item_code': d.item_code,
				'warehouse': cstr(d.s_warehouse) || cstr(d.t_warehouse),
				'transfer_qty': d.transfer_qty,
				'serial_no': d.serial_no,
				'bom_no': d.bom_no,
				'expense_account': d.expense_account,
				'cost_center': d.cost_center,
				'company': frm.doc.company,
				'qty': d.qty,
				'voucher_type': frm.doc.doctype,
				'voucher_no': d.name,
				'allow_zero_valuation': 1,
			};

			return frappe.call({
				doc: frm.doc,
				method: "get_item_details",
				args: args,
				callback: function (r) {
					if (r.message) {
						var d = locals[cdt][cdn];
						$.each(r.message, function (k, v) {
							if (v) {
								frappe.model.set_value(cdt, cdn, k, v); // qty and it's subsequent fields weren't triggered
							}
						});
						refresh_field("items");

					}
				}
			});
		}
	},
	lot_no: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		frappe.call({
			method: "ceramic.query.get_batch",
			args: {
				'args': {
					'item_code': d.item_code,
					'lot_no': d.lot_no
				},
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(d.doctype, d.name, 'batch_no', r.message)
				}
			}
		});
	},
});

erpnext.stock.select_batch_and_serial_no = (frm, item) => {
	let get_warehouse_type_and_name = (item) => {
		let value = '';
		if (frm.fields_dict.from_warehouse.disp_status === "Write") {
			value = cstr(item.s_warehouse) || '';
			return {
				type: 'Source Warehouse',
				name: value
			};
		} else {
			value = cstr(item.t_warehouse) || '';
			return {
				type: 'Target Warehouse',
				name: value
			};
		}
	}

	if (item && !item.has_serial_no && !item.has_batch_no) return;
	if (frm.doc.purpose === 'Material Receipt') return;

	frappe.require("assets/ceramic/js/utils/serial_no_batch_selector.js", function () {
		new erpnext.SerialNoBatchSelector({
			frm: frm,
			item: item,
			warehouse_details: get_warehouse_type_and_name(item),
		});
	});

}
