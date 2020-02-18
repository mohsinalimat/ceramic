// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sample', {
	// refresh: function(frm) {

	// }
	party: function (frm) {
		if (frm.doc.party) {
			frm.trigger("get_party_details");
		}
	},
	onload: function (frm) {
		if (frm.doc.party) {
			frm.trigger("get_party_details");
		}
	},
	get_party_details: function (frm) {
		frappe.call({
			method: "ceramic.api.get_party_details",
			args: {
				party: frm.doc.party,
				party_type: frm.doc.party_type
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value('party_name', r.message.party_name);
				}
			}
		});
	},
});
