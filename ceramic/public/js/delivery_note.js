frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
		// your code here
    },
    onload_post_render: function(frm){
		// hide delivery note from make button
		let $group = cur_frm.page.get_inner_group_button("Create");
		
		let li_length = $group.find("ul li");
		for (let i = 0; i < li_length.length -1; i++) {		
			var li = $group.find(".dropdown-menu").children("li")[i];
			if (li.getElementsByTagName("a")[0].innerHTML == "Sales Invoice")
				$group.find(".dropdown-menu").children("li")[i].remove();
		}
	},
})