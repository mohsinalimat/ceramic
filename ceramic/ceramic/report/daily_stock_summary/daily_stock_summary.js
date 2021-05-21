// Copyright (c) 2016, Finbyz and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily Stock Summary"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
			"get_query": function() {
				return {
					filters: {
						'authority': 'Authorized'
					}
				}
			}
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default":frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname":"item_code",
			"label": __("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
		},
		{
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
	]
};


function create_production_entry(date,item_code,company) {
	let template = `
		<table class="table table-borderless" style="border: 0 !important; font-size:95%;">
		
			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><b>Date : </b>{{ date }}</td>
			</tr>

			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><b>Company : </b>{{ company }}</td>
			</tr>

			<tr style="border: 0 !important;">
			<td style="border: 0 !important;"><b>Item Code: </b> {{ item_code }}</td>
			</tr>

			<tr style="border: 0 !important;">
			
			<td>Enter Quantity:	<input type="float"  min="0" onkeypress="return (event.charCode == 8 || event.charCode == 0) ? null : event.charCode >= 48 && event.charCode <= 57" style="width:50px" id="get_qty_value"></input></td>
			
			<td style="border: 0 !important;">
			<td><button style="margin-left:5px;border:none;color: #fff; background-color: red; padding: 3px 5px;border-radius: 5px;" type="button" date="{{ date }}" item_code="{{ item_code }}" company="{{ company }}" onClick=create_stock_entry(this.getAttribute("date"),this.getAttribute("item_code"),this.getAttribute("company"),document.getElementById("get_qty_value").value)>Create Production Entry</button></td>
			</tr>
		</table>`;

		let message = frappe.template.compile(template)({ 'date':date,'company':company,'item_code':item_code});
		frappe.msgprint({
			message: message,
			title: "Production Details : " + item_code,
			wide: true
		});
}


function create_stock_entry(date,item_code,company,se_qty){
	$(".modal").modal('hide');
	frappe.call({
		method:"ceramic.ceramic.report.daily_stock_summary.daily_stock_summary._create_stock_entry",
		args:{
			date:date,
			item_code:item_code,
			company:company,
			se_qty:se_qty
		},
		callback: function(r){
		}
	})
}