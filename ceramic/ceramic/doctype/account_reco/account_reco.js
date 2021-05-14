// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.account.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
}
cur_frm.fields_dict.party.get_query = function (doc) {
	if (doc.party_type == 'Customer'){
		return {
			filters: {
				"is_primary_customer": 1,
				"disabled":0
			}
		}
	}
	else{
		return {
			filters: {
				"disabled":0
			}
		}
	}
}

frappe.ui.form.on('Account Reco', {
	// refresh: function(frm) {

	// }
});
