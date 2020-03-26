erpnext.selling.SalesOrderController = erpnext.selling.SalesOrderController.extend({
	price_list_rate: function(doc, cdt, cdn){
		let d = locals[cdt][cdn];
		frappe.call({
			method: "ceramic.ceramic.doc_events.sales_order.get_rate_discounted_rate",
			args: {
				"item_code": d.item_code,
				"customer": doc.customer,
				"company": doc.company
			},
			callback: function(r){
				if (r.message){
					frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
					frappe.model.set_value(cdt, cdn, 'discounted_rate', r.message.discounted_rate);
				}
			}
		});

		this.calculate_taxes_and_totals();
	},
	calculate_item_values: function() {
		var me = this;
		if (!this.discount_amount_applied) {
			$.each(this.frm.doc["items"] || [], function(i, item) {
				frappe.model.round_floats_in(item);
				item.net_rate = item.rate;

				if ((!item.qty) && me.frm.doc.is_return) {
					item.amount = flt(item.discounted_rate * -1, precision("amount", item));
				} else {
					item.amount = flt(item.discounted_rate * item.real_qty, precision("amount", item));
				}

				item.net_amount = item.amount;
				item.item_tax_amount = 0.0;
				item.total_weight = flt(item.weight_per_unit * item.stock_qty);

				me.set_in_company_currency(item, ["price_list_rate", "rate", "amount", "net_rate", "net_amount"]);
			});
		}
	},
})
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({frm: cur_frm}));

frappe.ui.form.on('Sales Order', {
	refresh: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
			console.log(1)
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
	company: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	// set_rate: function (frm) {
	// 		frm.doc.items.forEach(function (d) {
	// 		frappe.model.set_value(d.doctype, d.name, 'real_qty', d.qty);
	// 	});
	// },
	
})
frappe.ui.form.on("Sales Order Item", {
	// qty: function (frm, cdt, cdn) {
	// 	frm.events.set_rate(frm);
	// },

	item_code2: function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];

		frappe.call({
			method: "ceramic.ceramic.doc_events.sales_order.get_rate_discounted_rate",
			args: {
				"item_code": d.item_code,
				"customer": frm.doc.customer,
				"company": frm.doc.company
			},
			callback: function(r){
				if (r.message){
					frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
					frappe.model.set_value(cdt, cdn, 'discounted_rate', r.message.discounted_rate);
				}
			}
		});
	}
});