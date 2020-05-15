if (cur_frm.doc.party_type == "Customer") {
	
	cur_frm.fields_dict.customer.get_query = function (doc) {
		return {
			filters: {
				"disabled": 0
			}
		}
	};
}
// this.frm.cscript.onload = function (frm) {
// 	if (frm.doc.party_type == "Customer" || frm.doc.party_type == "Supplier") {
		
// 		frm.fields_dict.party.get_query = function (doc) {
// 			return {
// 				filters: {
// 					"disabled": 0
// 				}
// 			}
// 		};
// 	}

// }
frappe.ui.form.on('Payment Entry', {
	refresh: function(frm){
		if (frm.doc.__islocal){
			if (cur_frm.doc.company){
				frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
					frm.set_value('company_series', r.company_series);
				});
			}
			frm.trigger('company');
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
	company: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	}
});