frappe.provide("ceramic")
ceramic.restrict_access = {
    restrict_access: function(){
        frappe.call({
            method: 'ceramic.api.restrict_access',
            callback: function(r) {
                location.reload();
            }
        })
    }
}
