frappe.ui.form.on('BOM', {
	setup: function(frm){
		frm.set_query("item", function() {
			return {
				filters: {
					"item_group": frm.doc.item_group,
					// "name": ["LIKE", "%Premium%"],
					"is_stock_item": 1
				}
			}
		});
	},
	refresh: function(frm){
		
	},
});