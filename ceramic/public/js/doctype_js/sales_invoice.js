frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm){
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("ref_invoice", "");
		}
		if (!frm.doc.series_value){
			frm.trigger('naming_series');
		}
	},
	naming_series: function(frm) {
		let naming_series = frm.doc.naming_series
		frappe.call({
			method: "ceramic.api.check_counter_series",
			args: {
				'name': frm.doc.naming_series,
			},
			callback: function(r) {
				let a = r.message;
				frm.set_value("series_value", a);
			}
		});
	},
});