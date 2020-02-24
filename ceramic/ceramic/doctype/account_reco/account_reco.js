// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.account.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
}

frappe.ui.form.on('Account Reco', {
	// refresh: function(frm) {

	// }
});
