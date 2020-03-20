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
	qty: function (frm, cdt, cdn) {
		frm.events.set_rate(frm);
	}
});