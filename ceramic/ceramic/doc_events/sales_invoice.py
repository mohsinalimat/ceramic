import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.doctype.delivery_note.delivery_note import get_returned_qty_map,get_invoiced_qty_map
from frappe.contacts.doctype.address.address import get_company_address

def before_validate(self, method):
	self.flags.ignore_permissions = True
	
	for item in self.items:
		if not item.rate and item.delivery_childname:
			item.rate = frappe.db.get_value("Delivery Note Item", item.delivery_childname, 'discounted_rate')
		
		if not item.qty and item.delivery_childname:
			item.qty = frappe.db.get_value("Delivery Note Item", item.delivery_childname, 'real_qty')
		
		item.discounted_amount = (item.discounted_rate or 0)  * (item.real_qty or 0)
		item.discounted_net_amount = item.discounted_amount
	
	if self.authority == "Unauthorized":
		for item in self.items:
			item.full_rate = 0
			item.full_qty = 0
		
	if self.authority == "Authorized":
		for item in self.items:
			if not item.delivery_docname:
				if not item.full_rate:
					item.full_rate = item.rate

				if not item.full_qty:
					item.full_qty = item.qty
	
	if not self.primary_customer:
		self.primary_customer = self.customer
	
	if self.is_return:
		for item in self.items:
			item.full_qty = item.qty

def before_naming(self, method):
	if self.is_opening == "Yes":
		if not self.get('name'):
			self.naming_series = 'O' + self.naming_series

def on_submit(self, test):
	"""On Submit Custom Function for Sales Invoice"""
	create_main_sales_invoice(self)

def before_update_after_submit(self, method):
	"""On Update after Submit Custom Function for Sales Invoice"""
	update_linked_invoice(self)

def on_cancel(self, test):
	"""On Cancel Custom Function for Sales Invoice"""
	cancel_main_sales_invoice(self)

def on_trash(self, test):
	delete_sales_invoice(self)

def change_delivery_authority(name):
	dn_status = frappe.get_value("Delivery Note", name, "status")
	if dn_status == 'Completed':
		frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
	else:
		frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
	
# Create New Invouice on Submit
def create_main_sales_invoice(self):
	
	# Getting authority of company
	authority = frappe.db.get_value("Company", self.company, "authority")
	

	def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
		def set_target_values(source, target):
			target_company = frappe.db.get_value("Company", source.company, "alternate_company")
			target.company = target_company
			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

			target.si_ref = self.name
			target.authority = "Unauthorized"
			target.cost_center = source.cost_center.replace(source_company_abbr, target_company_abbr)
			if source.is_return:
				target.is_return = source.is_return
				target.return_against = frappe.db.get_value("Sales Invoice", source.return_against, 'si_ref')


			if source.debit_to:
				target.debit_to = source.debit_to.replace(source_company_abbr, target_company_abbr)
			if source.taxes_and_charges:
				taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
				if frappe.db.exists("Sales Taxes and Charges Template", taxes_and_charges):
					target.taxes_and_charges = taxes_and_charges
				else:
					target.taxes_and_charges = ''

			if source.taxes:
				for index, i in enumerate(source.taxes):
					target.taxes[index].charge_type = source.taxes[index].charge_type
					target.taxes[index].included_in_print_rate = source.taxes[index].included_in_print_rate
					if source.taxes[index].cost_center:
						target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)
					if source.taxes[index].account_head:
						target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
			if self.amended_from:
				name = frappe.db.get_value("Sales Invoice", {"si_ref": source.amended_from}, "name")
				target.amended_from = name

			target.set_missing_values()

		def account_details(source_doc, target_doc, source_parent):
			target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

			target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
			source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

			doc = frappe.get_doc("Company", target_company)

			target_doc.real_qty = source_doc.qty

			if source_doc.income_account:
				target_doc.income_account = source_doc.income_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.expense_account:
				target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
			if source_doc.cost_center:
				target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		fields = {
			"Sales Invoice": {
				"doctype": "Sales Invoice",
				"field_map": {
					"si_ref": "name",
					"is_opening": "is_opening"
				},
				"field_no_map":{
					"authority",
					"update_stock"
				}
			},
			"Sales Invoice Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"item_design": "item_code",
					"item_code": "item_design",
					"full_rate": "rate",
					"full_qty": "qty",
					"rate": "discounted_rate",
					"qty": "real_qty",
					"delivery_docname": "delivery_note",
					"delivery_childname": "dn_detail",
					"so_childname": "so_detail",
					"so_docname": "sales_order",
					"real_batch_no": "batch_no",
					"is_opening": "is_opening"
				},
				"field_no_map": {
					"full_rate",
					"full_qty",
					"series",
					"real_batch_no"
				},
				"postprocess": account_details,
			}
		}

		doclist = get_mapped_doc(
			"Sales Invoice",
			source_name,
			fields,
			target_doc,
			set_target_values,
			ignore_permissions=ignore_permissions
		)

		return doclist
		
	def make_si_from_dn(source_name, target_doc=None):
		doc = frappe.get_doc('Delivery Note', source_name)

		to_make_invoice_qty_map = {}
		returned_qty_map = get_returned_qty_map(source_name)
		invoiced_qty_map = get_invoiced_qty_map(source_name)

		def set_missing_values(source, target):
			target.ignore_pricing_rule = 1
			target.run_method("set_missing_values")
			target.run_method("set_po_nos")

			if len(target.get("items")) == 0:
				frappe.throw(_("All these items have already been invoiced"))

			target.run_method("calculate_taxes_and_totals")

			# set company address
			if source.company_address:
				target.update({'company_address': source.company_address})
			else:
				# set company address
				target.update(get_company_address(target.company))

			if target.company_address:
				target.update(get_fetch_values("Sales Invoice", 'company_address', target.company_address))

		def update_item(source_doc, target_doc, source_parent):
			target_company_income_account = frappe.db.get_value("Company", source_parent.company, "default_income_account")
			if target_company_income_account:
				target_doc.income_account = target_company_income_account

			target_doc.qty = to_make_invoice_qty_map[source_doc.name]
			
			if source_doc.serial_no and source_parent.per_billed > 0 and not source_parent.is_return:
				target_doc.serial_no = get_delivery_note_serial_no(source_doc.item_code,
					target_doc.qty, source_parent.name)

		def get_pending_qty(item_row):
			pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)

			returned_qty = 0
			if returned_qty_map.get(item_row.item_code, 0) > 0:
				returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
				returned_qty_map[item_row.item_code] -= pending_qty

			if returned_qty:
				if returned_qty >= pending_qty:
					pending_qty = 0
					returned_qty -= pending_qty
				else:
					pending_qty -= returned_qty
					returned_qty = 0

			to_make_invoice_qty_map[item_row.name] = pending_qty

			return pending_qty

		doc = get_mapped_doc("Delivery Note", source_name, {
			"Delivery Note": {
				"doctype": "Sales Invoice",
				"field_map": {
					"is_return": "is_return"
				},
				"validation": {
					"docstatus": ["=", 1]
				}
			},
			"Delivery Note Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "dn_detail",
					"parent": "delivery_note",
					"so_detail": "so_detail",
					"against_sales_order": "sales_order",
					"serial_no": "serial_no",
					"cost_center": "cost_center",
				},
				"postprocess": update_item,
				"filter": lambda d: get_pending_qty(d) <= 0 if not doc.get("is_return") else get_pending_qty(d) > 0
			},
			"Sales Taxes and Charges": {
				"doctype": "Sales Taxes and Charges",
				"add_if_empty": True
			},
			"Sales Team": {
				"doctype": "Sales Team",
				"field_map": {
					"incentives": "incentives"
				},
				"add_if_empty": True
			}
		}, target_doc, set_missing_values)

		return doc

	# If company is authorized then only cancel another invoice
	if self.items[0].delivery_docname:
		delivery_doc = frappe.get_doc("Delivery Note", self.items[0].delivery_docname)
		
	if authority == "Authorized" and not self.dont_replicate:
		if self.items[0].delivery_docname:
			if delivery_doc.discounted_grand_total == self.grand_total:
				si = make_si_from_dn(delivery_doc.name)
			else:
				si = get_sales_invoice_entry(self.name)
		else:
			si = get_sales_invoice_entry(self.name)
		si.naming_series = 'A' + str(self.company_series) + self.naming_series
		si.series_value = self.series_value
		si.flags.ignore_permissions = True
		si.si_ref = self.name
		si.set_posting_time = self.set_posting_time
		si.posting_date = self.posting_date
		si.posting_time = self.posting_time
		if self.amended_from:
			si.amended_from = frappe.db.get_value("Sales Invoice", {"si_ref": self.amended_from}, "name")
		si.save(ignore_permissions = True)
		for tax in si.taxes:
			if tax.tax_exclusive and tax.charge_type != "Actual":
				tax.included_in_print_rate = 1
		si.save(ignore_permissions = True)
		si.pay_amount_left = si.rounded_total - self.rounded_total
		if si.pay_amount_left < 0:
			si.pay_amount_left = 0.0
		si.save(ignore_permissions = True)
		self.db_set('si_ref', si.name)
		si.submit()
	
	if authority == "Unauthorized" and not self.si_ref:
		self.db_set('pay_amount_left', self.rounded_total)

def validate(self, method):
	update_discounted_net_total(self)

def update_discounted_net_total(self):
	self.discounted_total = sum(x.discounted_amount for x in self.items)
	self.discounted_net_total = sum(x.discounted_net_amount for x in self.items)
	testing_only_tax = 0
	
	for tax in self.taxes:
		if tax.testing_only:
			testing_only_tax += tax.tax_amount
	
	self.discounted_grand_total = self.discounted_net_total + self.total_taxes_and_charges - testing_only_tax
	self.discounted_rounded_total = round(self.discounted_grand_total)
	self.real_difference_amount = self.rounded_total - self.discounted_rounded_total

def update_linked_invoice(self):
	self.flags.ignore_validate_update_after_submit = True
	if self.si_ref:
		si = frappe.get_doc("Sales Invoice",self.si_ref)
		si.db_set('sales_partner',self.sales_partner)
		si.db_set('primary_customer',self.primary_customer)
		if self.sales_team:
			for row in self.sales_team:
				si.append('sales_team',{
					'sales_person': row.sales_person,
					'contact_no': row.contact_no,
					'allocated_percentage': row.allocated_percentage,
					'allocated_amount': row.allocated_amount,
					'commission_rate': row.commission_rate,
					'incentives': row.incentives,
					'company': row.company,
					'regional_sales_manager': row.regional_sales_manager,
					'sales_manager': row.sales_manager
				})

# Cancel Invoice on Cancel
def cancel_main_sales_invoice(self):
	if self.si_ref:
		si = frappe.get_doc("Sales Invoice", {'si_ref':self.name})
	else:
		si = None
	
	if si:
		if si.docstatus == 1:
			si.flags.ignore_permissions = True
			try:
				si.cancel()
				for i in self.items:
					change_delivery_authority(i.delivery_docname)
			except Exception as e:
				frappe.db.rollback()
				frappe.throw(e)
	else:
		for i in self.items:
			change_delivery_authority(i.delivery_docname)

def delete_sales_invoice(self):
	ref_name = self.si_ref
	frappe.db.set_value("Sales Invoice", self.name, 'si_ref', '')    
	frappe.db.set_value("Sales Invoice", ref_name, 'si_ref', '') 
	frappe.delete_doc("Sales Invoice", ref_name, force = 1, ignore_permissions=True)  
