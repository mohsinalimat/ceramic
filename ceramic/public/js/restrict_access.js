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
if (frappe.user.has_role("Local Admin")){
    frappe.db.get_value('Global Defaults', 'Global Defaults', 'restricted_access')
        .then(r => {
            let check = r.message.restricted_access;
            if (check == 0){
                $(window).load(function () {
                    $("#toolbar-help").append('<a class="dropdown-item" href="#" onclick="return ceramic.restrict_access.restrict_access();">Restrict Access</a>');
                });
            }
        });
}