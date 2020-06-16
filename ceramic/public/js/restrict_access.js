function restrict_access(){
    frappe.call({
        method: 'ceramic.api.restrict_access',
        callback: function(r) {
            location.reload();
        }
    })
    
}