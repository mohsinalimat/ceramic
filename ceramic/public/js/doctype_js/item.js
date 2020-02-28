cur_frm.fields_dict.item_series.get_query = function(doc) {
	return {
		filters: {
			"authority": "Authorized",
		}
	}
};
frappe.ui.form.on('Item', {
	refresh(frm) {
		// your code here
	}
});