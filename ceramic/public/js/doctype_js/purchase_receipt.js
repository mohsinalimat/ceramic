frappe.ui.form.on('Purchase Receipt', {
	refresh: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
			console.log(1)
			frappe.call({
				method: "ceramic.api.check_counter_series",
				args: {
					'name': frm.doc.naming_series,
					'company_series': frm.doc.company_series,
				},
				callback: function(e) {
					frm.set_value("series_value", e.message);
				}
			});
		}
	},
	company: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
    onload_post_render: function(frm){
		frm.trigger('pi_menu_hide');
	},
	on_submit: function(frm){
		frm.trigger('pi_menu_hide');
	},
	pi_menu_hide: function(frm){
		
		let $group = cur_frm.page.get_inner_group_button("Create");
				
		let li_length = $group.find("ul li");
		for (let i = 0; i < li_length.length -1; i++) {		
			var li = $group.find(".dropdown-menu").children("li")[i];
			if (li.getElementsByTagName("a")[0].innerHTML == "Purchase Invoice")
				$group.find(".dropdown-menu").children("li")[i].remove();
		}
		
		if (!frm.doc.__islocal && frm.doc.docstatus == 1 && frm.doc.status != 'Cancelled') {
			frm.add_custom_button(__("Purchase Invoice"), function () {
				frappe.model.open_mapped_doc({
					method: "ceramic.ceramic.doc_events.purchase_receipt.make_purchase_invoice",
                    frm: cur_frm
				})
			},
			__("Create"));
			frm.add_custom_button(__("Purchase Invoice Test"), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
					frm: cur_frm
				})
			},
			__("Create"));
		}
	}
});