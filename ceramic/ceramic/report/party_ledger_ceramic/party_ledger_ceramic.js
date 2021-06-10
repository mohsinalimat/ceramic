// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.query_reports["Party Ledger Ceramic"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
			get_query: () => {
				var company = frappe.query_report.get_filter_value('company');
				return {
					filters: {
						'authority': 'Unauthorized'
					}
				}
			}
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -3),
			"reqd": 1,
			"width": "40px"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
			"width": "40px"
		},
		{
			"fieldname":"party_type",
			"label": __("Party Type"),
			"fieldtype": "Link",
			"options": "Party Type",
			"default": "Customer",
			get_query: () => {
				return {
					filters: {
						name : ['in', ['Customer', 'Supplier']]
					}
				}
			}
		},
		{
			"fieldname":"party",
			"label": __("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": "80px"
		},
		{
			"fieldname":"primary_customer",
			"label": __("Primary Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": "80px",
			get_query: () => {
				return { query: "ceramic.controllers.queries.new_customer_query" }
			}
		},
		{
			"label": __("Print With Item"),
			"fieldname": "print_with_item",
			"fieldtype": "Check"
		},	
		{
			"label": __("Show Unlinked Transactions"),
			"fieldname": "show_unlinked_transactions",
			"fieldtype": "Check"
		},	
		{
			"label": __("Show Only Unlinked Transactions"),
			"fieldname": "show_only_unlinked_transactions",
			"fieldtype": "Check"
		},	
	],
	onload: function(report){
		display_qr()
		frappe.call({
			method:"finbyzerp.whatsapp_manager.get_whatsapp_settings",
			args:{},
			callback: function(r){
				if (r.message ==true){
					report.page.add_menu_item(__('Send WhatsApp'), function() {
						whatsapp_dialog(report)
					});
				}
			}
			
		})
	
	}
};
function whatsapp_dialog(report){
    var dialog = new frappe.ui.Dialog({
        title: 'Send Whatsapp',
        no_submit_on_enter: true,
        width: 400,
        fields: [
            {label:'Mobile Number', fieldtype:'Data', fieldname:'number', reqd:1},
			{
				label:__("Message"),
				fieldtype:"Small Text",
				fieldname:"content",
				default:"**Do Not Reply Here**\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tthis is an unattended account"
			},
			{fieldtype: "Section Break"},
            {label:'',fieldtype:'Read Only',default:" Note : Please ensure that Internet Connection is available on your Whatsapp device."},
        ],
        primary_action_label: 'Send',
        primary_action(values) {
			var filters={};
			report.filters.forEach(function(lst){
				if (lst.value){
					filters[lst.fieldname] = lst.value
					}
					if (lst.fieldname=='print_with_item' && lst.last_value==1){
						filters[lst.fieldname] = lst.last_value
					}
				});
				frappe.call({
					method:"ceramic.ceramic.report.party_ledger_ceramic.party_ledger_ceramic.get_report_data_pdf",
					args:{
						"filters":filters
					},
					callback: function(d){
						let data = d.message[1]
						let columns = d.message[0]
						let print_settings = {"with_letter_head":0,"orientation":"Landscape"}
						const custom_format = report.report_settings.html_format
						const content = frappe.render_template(custom_format, {
							'title': "Party Ledger Ceramic",
							'subtitle':"Filters",
							'data': data,
							'columns': columns,
							'filters':filters
						});
						const base_url = frappe.urllib.get_base_url();
						const print_css = frappe.boot.print_css;
						const html = frappe.render_template('print_template', {
							title: "Party Ledger Ceramic",
							content: content,
							base_url: base_url,
							print_css: print_css,
							print_settings:{"with_letter_head":0,"orientation":"Landscape"},
							landscape:true,
							columns: d.message[0]
					});
					
					frappe.call({
						method:"ceramic.ceramic.report.party_ledger_ceramic.party_ledger_ceramic.generate_report_pdf",
						args:{
							"html":html,
							'filters':filters
						},
						callback: function(p){
							var v = dialog.get_values();
							frappe.show_alert({message:__("Sending Whatsapp..."), indicator:'green'})
							frappe.call({
								method:"ceramic.ceramic.report.party_ledger_ceramic.party_ledger_ceramic.get_report_pdf_whatsapp",
								args:{
									mobile_number:v.number,
									content:v.content || false,
									file_url:p.message.file_url,
									file_name:p.message.file_name,
									filters:p.message.filters
								},
								callback: function(r){
								}
							})
						}
					})
				}
			})
		dialog.hide()
    }
    });
    dialog.show();
};

function display_qr(){
	let event = String('Party Ledger Ceramic' + frappe.session.user)
    frappe.realtime.on(event, function(data) {
        var d = frappe.msgprint({
            title: __('Scan below QR Code in Whatsapp Web'),
            message: data,
            // "<img src='/private/files/'"+frappe.session.user + "'.png' alt='No Image'>",
            primary_action:{
                action(values) {
                    d.hide()
                }
            }
        });    
        setTimeout(function(){$(".modal.fade.in").modal('hide');},10000)    
    })
};

function create_account_reco(posting_date,company,alternate_company,account,alternate_account,reconciled_amount,alternate_reconciled_amount,party_type,party) {
	frappe.confirm(
		__('<h4><b>Are you sure you want to Create Account Reco Entry ?</b></h4>' +'<br/>\
		Posting Date: <b>' + posting_date + '</b><br/>' + 
		'Company: <b>' + alternate_company + '</b><br/>' + 
		'Account: <b>' + alternate_account + '</b><br/>' + 
		'Reconciled Amount: <b>' + alternate_reconciled_amount + '</b><br/>' + 
		'Party Type: <b>'+ party_type + '</b><br/>' + 
		'Party: <b>'+ party + '</b>'),
		function(){
			frappe.call({
				method:"ceramic.ceramic.report.party_ledger_ceramic.party_ledger_ceramic.create_account_reco_entry",
				freeze:true,
				args:{
					"posting_date":posting_date,
					"company":company,
					"alternate_company":alternate_company,
					"account":account,
					"alternate_account":alternate_account,
					"reconciled_amount":reconciled_amount,
					"alternate_reconciled_amount":alternate_reconciled_amount,
					"party_type":party_type,
					"party":party
				}
			})
		}
	)

	
}