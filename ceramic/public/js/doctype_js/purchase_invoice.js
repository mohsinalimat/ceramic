cur_frm.fields_dict.taxes_and_charges.get_query = function(doc) {
	return {
		filters: {
			"docstatus": 0 && 1,
			"company": doc.company
		}
	}
};

this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [

				['is_purchase_item', '=', 1],
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
}
frappe.ui.form.on('Purchase Invoice', {
	refresh: function(frm){
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("ref_invoice", "");
		}
		if (cur_frm.doc.company){
			frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
				frm.set_value('company_series', r.company_series);
			});
		}
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
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
	company: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	company_series: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	}
});