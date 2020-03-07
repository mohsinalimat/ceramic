frappe.ui.form.on('Stock Entry', {
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
							let item_row = frappe.model.add_child(frm.doc,'Stock Entry Detail','items');
							// item_row.item_code = new_name;
							frappe.model.set_value(item_row.doctype, item_row.name, 'item_code', new_name);
							frappe.model.set_value(item_row.doctype, item_row.name, 'qty', 0);
							get_item_details(new_name).then(data => {
								console.log(data)
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
						
						var new_name = originial_item["item_detail"].	replace('-I-',item);
						
						let item_row = frappe.model.add_child(frm.doc,'Stock Entry Detail','items');
						// item_row.item_code = new_name;

						frappe.model.set_value(item_row.doctype, item_row.name, 'item_code', new_name);
						frappe.model.set_value(item_row.doctype, item_row.name, 'qty', 0);
						get_item_details(new_name).then(data => {
							console.log(data)
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

		frm.refresh_field('items');
	},
	before_validate: function (frm) {
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
});