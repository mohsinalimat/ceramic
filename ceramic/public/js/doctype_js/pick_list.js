frappe.ui.form.on('Pick List', {
	refresh(frm) {

	},
	update_items: function(frm){
		select_items({frm: frm});
	},
});

const select_items = (args) => {
	frappe.require("assets/ceramic/js/utils/item_selector.js", function() {
		new ItemSelector(args)
	})
}