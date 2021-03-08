frappe.ui.form.on('User', {
    refresh: function (frm) {
		frm.add_custom_button(__('Remove Authentication'), function() {
            frappe.call({
                method:"ceramic.api.remove_authentication",
                args:{
                    user:frm.doc.name
                }
            })
            
        })
	},
})