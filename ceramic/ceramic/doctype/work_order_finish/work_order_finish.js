// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt
frappe.provide("erpnext.stock");

cur_frm.fields_dict.source_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
}

cur_frm.fields_dict.target_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
}

frappe.ui.form.on('Work Order Finish', {
	setup: function(frm){
		frm.set_query("finish_item", function() {
			return {
				filters: {
					"name": ["LIKE", "%Premium%"],
					"is_stock_item": 1,
				}
			}
		});
		frm.set_query("expense_account", "additional_cost", function () {
			return {
				query: "erpnext.controllers.queries.tax_account_query",
				filters: {
					"account_type": ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation", "Expenses Included In Asset Valuation"],
					"company": frm.doc.company
				}
			};
		});
	},
	get_item:function(frm){
		if(!frm.doc.items){
			frm.doc.items = []
		}
		if(!frm.doc.finish_item){
			frm.doc.finish_item = []
		}
		var finish_item_list = [];
		var item_list = [];
		var categories = ['Premium','Golden','Economy','Classic'];
		var i = 0;
		var new_item_list = [];

		for (i = 0; i < frm.doc.finish_item.length; i++){
			finish_item_list.push(frm.doc.finish_item[i].item_detail.replace(frm.doc.finish_item[i].item_detail.split("-").splice(-1), ''))
		}
		
		for (i = 0; i < frm.doc.items.length; i++){
			item_list.push(frm.doc.items[i].item_code)
		}

		if (finish_item_list.length > 0){
			if (item_list.length > 0){
				for(i = 0; i < frm.doc.items.length; i++){
					var item = frm.doc.items[i].item_code.replace(frm.doc.items[i].item_code.split("-").splice(-1), '');
					if (finish_item_list.includes(item)){
						new_item_list.push(frm.doc.items[i]);
					}
				}
				
				frm.doc.items = new_item_list;

				for(i = 0; i < frm.doc.finish_item.length; i++){
					var count = 0;
					var finish_item = frm.doc.finish_item[i].item_detail.replace(frm.doc.finish_item[i].item_detail.split("-").splice(-1), '');

					for(var j = 0; j < frm.doc.items.length; j++){
						var item = frm.doc.items[j].item_code.replace(frm.doc.items[i].item_code.split("-").splice(-1), '');
						if (finish_item == item){
							count++;
						}
					}

					if(count === 0){
						for(var j = 0; j < categories.length; j++){
							var new_name = finish_item + categories[j];
							let item_row = frm.add_child("items");
							frappe.model.set_value(item_row.doctype, item_row.name , 'item_code', new_name);
							frappe.model.set_value(item_row.doctype, item_row.name , 'qty', 1);
							// console.log(item_row.doctype);
							// console.log(item_row.name);
							// item_row.item_code = new_name;
							get_item_details(item_row.item_code).then(data => {
								frappe.model.set_value(item_row.doctype, item_row.name , 'uom', data.stock_uom);
								// frappe.model.set_value(item_row.doctype, item_row.name , 'stock_uom', data.stock_uom);
								frappe.model.set_value(item_row.doctype, item_row.name , 'conversion_factor', 1);
							});
						}
					}
				}
				frm.refresh_field('items');
			} else {
				frm.doc.finish_item.forEach(function(originial_item, index){
					categories.forEach(function (item, index){
						
						var new_name = originial_item["item_detail"].replace(originial_item["item_detail"].split("-").splice(-1),item);
						
						let item_row = frm.add_child("items");
						frappe.model.set_value(item_row.doctype, item_row.name , 'item_code', new_name);
						frappe.model.set_value(item_row.doctype, item_row.name , 'qty', 1);
						// console.log(item_row.doctype);
						// console.log(item_row.name);
						get_item_details(item_row.item_code).then(data => {
							frappe.model.set_value(item_row.doctype, item_row.name , 'uom', data.stock_uom);
							// frappe.model.set_value(item_row.doctype, item_row.name , 'stock_uom', data.stock_uom);
							frappe.model.set_value(item_row.doctype, item_row.name , 'conversion_factor', 1);
						});
					});
				});
				frm.refresh_field('items');
			}
		} else {
			frm.doc.items = [];
		}

		for(i = 0; i < frm.doc.items.length; i++){
			frm.doc.items[i].idx = i + 1;
		}

		frm.refresh_field('items');
	},

	before_save: function(frm){
		frm.trigger("cal_total");
	},
	 cal_total: function(frm){
		let total_amount = 0.0;
		let total_Qty = 0.0;
		let total_amount_itmes = 0.0;
	
		
		frm.doc.additional_cost.forEach(function (d) {
			total_amount += d.amount;
		});
		frm.doc.items.forEach(function (d){
			total_Qty +=d.qty;
			total_amount_itmes +=d.amount;
			frappe.model.set_value(d.doctype,d.name,"basic_amount",flt(d.qty * d.basic_rate));
		});
		frm.set_value("total_additional_cost",total_amount);
		frm.set_value("total_qty",total_Qty);
		frm.set_value("total_amount",total_amount_itmes);
		
	},

	set_basic_rate: function (frm, cdt, cdn) {
		const item = locals[cdt][cdn];
		item.transfer_qty = flt(item.qty) * flt(item.conversion_factor);

		const args = {
			'item_code': item.item_code,
			'posting_date': frm.doc.posting_date,
			'posting_time': frm.doc.posting_time,
			'warehouse': cstr(item.s_warehouse) || cstr(item.t_warehouse),
			'serial_no': item.serial_no,
			'company': frm.doc.company,
			'qty': item.s_warehouse ? -1 * flt(item.transfer_qty) : flt(item.transfer_qty),
			'voucher_type': frm.doc.doctype,
			'voucher_no': item.name,
			'allow_zero_valuation': 1,
		};

		if (item.item_code || item.serial_no) {
			frappe.call({
				method: "erpnext.stock.utils.get_incoming_rate",
				args: {
					args: args
				},
				callback: function (r) {
					frappe.model.set_value(cdt, cdn, 'basic_rate', (r.message || 0.0));
					frm.events.calculate_basic_amount(frm, item);
				}
			});
		}
	},

	get_warehouse_details: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (!child.bom_no) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_warehouse_details",
				args: {
					"args": {
						'item_code': child.item_code,
						'warehouse': cstr(child.s_warehouse) || cstr(child.t_warehouse),
						'transfer_qty': child.transfer_qty,
						'serial_no': child.serial_no,
						'qty': child.s_warehouse ? -1 * child.transfer_qty : child.transfer_qty,
						'posting_date': frm.doc.posting_date,
						'posting_time': frm.doc.posting_time,
						'company': frm.doc.company,
						'voucher_type': frm.doc.doctype,
						'voucher_no': child.name,
						'allow_zero_valuation': 1
					}
				},
				callback: function (r) {
					if (!r.exc) {
						$.extend(child, r.message);
						frm.events.calculate_basic_amount(frm, child);
					}
				}
			});
		}
	},

	calculate_basic_amount: function (frm, item) {
		item.basic_amount = flt(flt(item.transfer_qty) * flt(item.basic_rate),
			precision("basic_amount", item));

		frm.events.calculate_amount(frm);
	},

	calculate_amount: function (frm) {
		frm.events.calculate_total_additional_costs(frm);

		const total_basic_amount = frappe.utils.sum(
			(frm.doc.items || []).map(function (i) { return i.t_warehouse ? flt(i.basic_amount) : 0; })
		);

		for (let i in frm.doc.items) {
			let item = frm.doc.items[i];

			if (item.t_warehouse && total_basic_amount) {
				item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs;
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost),
				precision("amount", item));

			item.valuation_rate = flt(flt(item.basic_rate)
				+ (flt(item.additional_cost) / flt(item.transfer_qty)),
				precision("valuation_rate", item));
		}

		refresh_field('items');
	},

	calculate_total_additional_costs: function (frm) {
		const total_additional_costs = frappe.utils.sum(
			(frm.doc.additional_cost || []).map(function (c) { return flt(c.amount); })
		);

		frm.set_value("total_additional_cost",
			flt(total_additional_costs, precision("total_additional_cost")));
	},
});

frappe.ui.form.on('Work Order Finish Item', {
	qty: function (frm, cdt, cdn) { 
		frm.events.set_basic_rate(frm, cdt, cdn);
		var d = locals[cdt][cdn];
		frappe.model.set_value(d.doctype, d.name, "basic_amount", flt(d.qty * d.basic_rate))

		// if (d.item_code) {
		//     var args = {
		//         'item_code': d.item_code,
		//         'warehouse': cstr(d.s_warehouse) || cstr(d.t_warehouse),
		//         'transfer_qty': d.transfer_qty,
		//         'serial_no': d.serial_no,
		//         'bom_no': d.bom_no,
		//         'expense_account': d.expense_account,
		//         'cost_center': d.cost_center,
		//         'company': frm.doc.company,
		//         'qty': d.qty,
		//         'voucher_type': frm.doc.doctype,
		//         'voucher_no': d.name,
		//         'allow_zero_valuation': 1,
		//     };

		//     return frappe.call({
		//         doc: frm.doc,
		//         method: "get_item_details",
		//         args: args,
		//         callback: function (r) {
		//             if (r.message) {
		//                 var d = locals[cdt][cdn];
		//                 $.each(r.message, function (k, v) {
		//                     d[k] = v;
		//                 });
		//                 frm.events.calculate_amount(frm);
		//                 refresh_field("items");
		//             }
		//         }
		//     });
		// }
	},
	conversion_factor: function (frm, cdt, cdn) {
		frm.events.set_basic_rate(frm, cdt, cdn);
	},
	t_warehouse: function (frm, cdt, cdn) {
		frm.events.get_warehouse_details(frm, cdt, cdn);
	},

	basic_rate: function (frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		frm.events.calculate_basic_amount(frm, d);
		frappe.model.set_value(d.doctype, d.name, "basic_amount", flt(d.qty * d.basic_rate))

	},
	uom: function (doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		if (d.uom && d.item_code) {
			return frappe.call({
				method: "erpnext.stock.doctype.stock_entry.stock_entry.get_uom_details",
				args: {
					item_code: d.item_code,
					uom: d.uom,
					qty: d.qty
				},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, r.message);
					}
				}
			});
		}
	},
	// item_code: function (frm, cdt, cdn) {
	// 	var d = locals[cdt][cdn];
	// 	if (d.item_code) {
	// 		var args = {
	// 			'item_code': d.item_code,
	// 			'warehouse': cstr(d.s_warehouse) || cstr(d.t_warehouse),
	// 			'serial_no': d.serial_no,
	// 			'expense_account': d.expense_account,
	// 			'cost_center': d.cost_center,
	// 			'company': frm.doc.company,
	// 			'qty': d.qty,
	// 		};

	// 		return frappe.call({
	// 			doc: frm.doc,
	// 			method: "get_item_details",
	// 			args: args,
	// 			callback: function (r) {
	// 				if (r.message) {
	// 					$.each(r.message, function (key, value) {
	// 						frappe.model.set_value(d.doctype,d.name,key,value);
	// 					});
	// 					frm.events.calculate_amount(frm);
	// 					refresh_field("items");
	// 				}
	// 			}
	// 		});
	// 	}
	// },
	expense_account: function (frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "expense_account");
	},
	cost_center: function (frm, cdt, cdn) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "cost_center");
	},
});

function get_item_details(item_code) {
	if (item_code) {
		return frappe.xcall('erpnext.stock.doctype.pick_list.pick_list.get_item_details', {
			item_code
		})
	}
}