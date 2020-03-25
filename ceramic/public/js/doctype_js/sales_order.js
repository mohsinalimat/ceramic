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
	set_rate: function (frm) {
			frm.doc.items.forEach(function (d) {
			frappe.model.set_value(d.doctype, d.name, 'real_qty', d.qty);
		});
	},
	
})
frappe.ui.form.on("Sales Order Item", {
	// qty: function (frm, cdt, cdn) {
	// 	frm.events.set_rate(frm);
	// },

	item_code: function(frm, cdt, cdn) {
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
					// d.rate = 0
					// d.discounted_rate = 0
					frappe.model.set_value(cdt, cdt, 'rate', r.message.rate);
					// frappe.model.set_value(cdt, cdt, 'discounted_rate', r.message.discounted_rate);
					console.log(r.message);
					frm.refresh_field('items');
				}
			}
		});
	}
});