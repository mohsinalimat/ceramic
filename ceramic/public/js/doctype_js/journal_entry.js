frappe.ui.form.on('Journal Entry', {
    before_save: function(frm){
        if (frm.doc.company && frm.doc.accounts){
            frm.doc.accounts.forEach(function(row){
                if(!row.cost_center){
                    frappe.db.get_value("Company",frm.doc.company,"cost_center",function(r){
					    frappe.model.set_value(row.doctype,row.name,"cost_center",r.cost_center)
					})
                }
            })
        }
    }
})