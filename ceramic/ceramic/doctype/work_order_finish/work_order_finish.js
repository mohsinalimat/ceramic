// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order Finish', {
	// refresh: function(frm) {

	// }
	get_item:function(frm){
        frm.set_value('items',[])
        // if(frm.doc.get_items_from == "Sales Order"){ 
		frm.doc.finish_item.forEach(function(d) {
			frappe.model.with_doc("Item", d.sales_order, function() {
				var so_doc = frappe.model.get_doc("Sales Order", d.sales_order)
				$.each(so_doc.items, function(index, row){
					let fi = frm.add_child("finish_items");
					fi.item_code = row.item_code
					fi.outward_sample = row.outward_sample
					fi.quantity = row.qty
					fi.sales_order = d.sales_order
				})          
				frm.refresh_field("finish_items");
			});      
		});
        // }
        
    // },
    // get_items_from:function(frm){
    //     frm.set_value('finish_items',[])
    //     frm.set_value('po_items',[])
    // }
});
