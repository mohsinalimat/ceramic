frappe.ui.form.on('User', {
    refresh: function (frm) {
		frm.add_custom_button(__('Remove Authentication'), function() {
            frappe.confirm('Are you sure you want to remove authentication?',
            () =>{
                frappe.db.set_default(frm.doc.name + '_otplogin',None)},
                frappe.msgprint("Authentication Removed"),
            () =>{}
            )
        });
	},
})