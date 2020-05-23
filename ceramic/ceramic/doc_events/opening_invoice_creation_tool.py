import frappe
from frappe import _
from frappe.utils import flt
from frappe import _, scrub


def make_invoices(self):
	names = []
	authority = frappe.db.get_value("Company", self.company, 'authority')
	alternate_company = frappe.db.get_value("Company", self.company, 'alternate_company')
	source_abbr = frappe.db.get_value("Company", self.company, 'abbr')
	target_abbr = frappe.db.get_value("Company", alternate_company, 'abbr')
	mandatory_error_msg = _("Row {0}: {1} is required to create the Opening {2} Invoices")
	if not self.company:
		frappe.throw(_("Please select the Company"))

	for row in self.invoices:
		if not row.qty:
			row.qty = 1.0

		# always mandatory fields for the invoices
		if not row.temporary_opening_account:
			row.temporary_opening_account = get_temporary_opening_account(self.company)
		row.party_type = "Customer" if self.invoice_type == "Sales" else "Supplier"

		# Allow to create invoice even if no party present in customer or supplier.
		if not frappe.db.exists(row.party_type, row.party):
			if self.create_missing_party:
				self.add_party(row.party_type, row.party)
			else:
				frappe.throw(_("{0} {1} does not exist.").format(frappe.bold(row.party_type), frappe.bold(row.party)))

		if not row.item_name:
			row.item_name = _("Opening Invoice Item")
		if not row.posting_date:
			row.posting_date = nowdate()
		if not row.due_date:
			row.due_date = nowdate()

		if authority == "Unauthorized":
			for d in ("Party", "Outstanding Amount", "Temporary Opening Account"):
				if not row.get(scrub(d)):
					frappe.throw(mandatory_error_msg.format(row.idx, _(d), self.invoice_type))

		args = self.get_invoice_dict(row=row)
		
		if not args:
			continue
		if row.outstanding_amount > 0.0:
			if row.outstanding_amount <= row.full_amount:
				doc = frappe.get_doc(args).insert()
				if doc.doctype == 'Sales Invoice':
					doc.sales_partner = row.sales_partner
				doc.primary_customer = row.primary_customer
			else:
				difference = row.outstanding_amount - row.full_amount
				# frappe.throw(str(difference))
				args['items'][0]['full_rate'] = args['items'][0]['rate']
				doc = frappe.get_doc(args).insert()
				if doc.doctype == 'Sales Invoice':
					doc.sales_partner = row.sales_partner
				doc.primary_customer = row.primary_customer
				
				doc2 = frappe.new_doc("Journal Entry")
				doc2.primary_customer = row.primary_customer
				doc2.voucher_type = "Credit Note" if self.invoice_type == 'Sales' else "Debit Note"
				doc2.posting_date = row.posting_date
				doc2.sales_partner = row.sales_partner if self.invoice_type == 'Sales' else None
				doc2.company = alternate_company
				doc2.is_opening = 'Yes'
				if self.invoice_type == 'Sales':
					doc2.append('accounts', {
						'account': frappe.get_value("Company", doc2.company, 'default_receivable_account'),
						'party_type': 'Customer',
						'party': row.party,
						'debit_in_account_currency': 0,
						'credit_in_account_currency': abs(difference),
						'is_advance': 'Yes'
					})

					doc2.append('accounts', {
						'account': row.temporary_opening_account.replace(source_abbr, target_abbr),
						'party_type': None,
						'party': None,
						'debit_in_account_currency': abs(difference),
						'credit_in_account_currency': 0
					})
				
				elif self.invoice_type == 'Purchase':
					doc2.append('accounts', {
						'account': frappe.get_value("Company", doc2.company, 'default_payable_account'),
						'party_type': 'Supplier',
						'party': row.party,
						'debit_in_account_currency': abs(difference),
						'credit_in_account_currency': 0,
						'is_advance': 'Yes'
					})

					doc2.append('accounts', {
						'account': row.temporary_opening_account.replace(source_abbr, target_abbr),
						'party_type': None,
						'party': None,
						'debit_in_account_currency': 0,
						'credit_in_account_currency': abs(difference)
					})
				
				doc2.save()
				doc2.submit()

				
			
			doc.submit()
			names.append(doc.name)

		elif flt(row.outstanding_amount) <= 0.0 and row.full_amount > 0.0:
			for item in args['items']:
				item['rate'] = flt(row.full_amount) / flt(item['qty'])
			doc = frappe.get_doc(args).insert()
			doc.company = frappe.db.get_value("Company", doc.company, 'alternate_company')
			doc.primary_customer = row.primary_customer
			for item in doc.items:
				item.rate = flt(row.full_amount) / flt(item.qty)
				item.cost_center = item.cost_center.replace(source_abbr, target_abbr)
				if doc.doctype == 'Sales Invoice':
					item.income_account = item.income_account.replace(source_abbr, target_abbr)
				elif doc.party_type == 'Purchase Invoice':
					item.expense_account = item.expense_account.replace(source_abbr, target_abbr)
			if doc.doctype == 'Sales Invoice':
				doc.debit_to = doc.debit_to.replace(source_abbr, target_abbr)
				doc.sales_partner = row.sales_partner
			elif doc.party_type == 'Purchase Invoice':
				doc.credit_to = doc.credit_to.replace(source_abbr, target_abbr)
			
			doc.submit()
			names.append(doc.name)
		
		if row.outstanding_amount < 0.0:
			doc = frappe.new_doc("Journal Entry")
			doc.voucher_type = "Credit Note" if self.invoice_type == 'Sales' else "Debit Note"
			doc.posting_date = row.posting_date
			doc.primary_customer = row.primary_customer
			doc.sales_partner = row.sales_partner if self.invoice_type == 'Sales' else None
			doc.company = self.company
			doc.is_opening = 'Yes'
			if self.invoice_type == 'Sales':
				doc.append('accounts', {
					'account': frappe.get_value("Company", doc.company, 'default_receivable_account'),
					'party_type': 'Customer',
					'party': row.party,
					'debit_in_account_currency': 0,
					'credit_in_account_currency': abs(row.outstanding_amount),
					'is_advance': 'Yes'
				})

				doc.append('accounts', {
					'account': row.temporary_opening_account,
					'party_type': None,
					'party': None,
					'debit_in_account_currency': abs(row.outstanding_amount),
					'credit_in_account_currency': 0
				})
			
			elif self.invoice_type == 'Purchase':
				doc.append('accounts', {
					'account': frappe.get_value("Company", doc.company, 'default_payable_account'),
					'party_type': 'Supplier',
					'party': row.party,
					'debit_in_account_currency': abs(row.outstanding_amount),
					'credit_in_account_currency': 0,
					'is_advance': 'Yes'
				})

				doc.append('accounts', {
					'account': row.temporary_opening_account,
					'party_type': None,
					'party': None,
					'debit_in_account_currency': 0,
					'credit_in_account_currency': abs(row.outstanding_amount)
				})
			
			doc.save()
			doc.submit()
		
		if row.outstanding_amount <= 0.0 and row.full_amount < 0.0:
			doc = frappe.new_doc("Journal Entry")
			doc.voucher_type = "Credit Note" if self.invoice_type == 'Sales' else "Debit Note"
			doc.posting_date = row.posting_date
			doc.sales_partner = row.sales_partner if self.invoice_type == 'Sales' else None
			doc.primary_customer = row.primary_customer
			doc.company = alternate_company
			doc.is_opening = 'Yes'
			if self.invoice_type == 'Sales':
				doc.append('accounts', {
					'account': frappe.get_value("Company", doc.company, 'default_receivable_account'),
					'party_type': 'Customer',
					'party': row.party,
					'debit_in_account_currency': 0,
					'credit_in_account_currency': abs(row.full_amount),
					'is_advance': 'Yes'
				})

				doc.append('accounts', {
					'account': row.temporary_opening_account.replace(source_abbr, target_abbr),
					'party_type': None,
					'party': None,
					'debit_in_account_currency': abs(row.full_amount),
					'credit_in_account_currency': 0
				})
			
			elif self.invoice_type == 'Purchase':
				doc.append('accounts', {
					'account': frappe.get_value("Company", doc.company, 'default_payable_account'),
					'party_type': 'Supplier',
					'party': row.party,
					'debit_in_account_currency': abs(row.full_amount),
					'credit_in_account_currency': 0,
					'is_advance': 'Yes'
				})

				doc.append('accounts', {
					'account': row.temporary_opening_account.replace(source_abbr, target_abbr),
					'party_type': None,
					'party': None,
					'debit_in_account_currency': 0,
					'credit_in_account_currency': abs(row.full_amount)
				})
			
			doc.save()
			doc.submit()

		if len(self.invoices) > 5:
			frappe.publish_realtime(
				"progress", dict(
					progress=[row.idx, len(self.invoices)],
					title=_('Creating {0}').format(doc.doctype)
				),
				user=frappe.session.user
			)

	return names

def get_invoice_dict(self, row=None):
	def get_item_dict():
		default_uom = frappe.db.get_single_value("Stock Settings", "stock_uom") or _("Nos")
		cost_center = frappe.get_cached_value('Company',  self.company,  "cost_center")
		if not cost_center:
			frappe.throw(
				_("Please set the Default Cost Center in {0} company.").format(frappe.bold(self.company))
			)
		row.outstanding_amount = flt(row.outstanding_amount)
		row.full_amount = flt(row.full_amount)
		rate = flt(row.outstanding_amount) / flt(row.qty)
		full_rate = flt(row.full_amount) / flt(row.qty)
		# frappe.throw(str(rate))

		return frappe._dict({
			"uom": default_uom,
			"rate": rate or 0.0,
			"qty": row.qty,
			"full_qty": row.qty,
			"full_rate": full_rate or 0.0,
			"conversion_factor": 1.0,
			"item_name": row.item_name or "Opening Invoice Item",
			"description": row.item_name or "Opening Invoice Item",
			income_expense_account_field: row.temporary_opening_account,
			"cost_center": cost_center
		})

	if not row:
		return None

	party_type = "Customer"
	income_expense_account_field = "income_account"
	if self.invoice_type == "Purchase":
		party_type = "Supplier"
		income_expense_account_field = "expense_account"

	item = get_item_dict()

	args = frappe._dict({
		"items": [item],
		"is_opening": "Yes",
		"set_posting_time": 1,
		"company": self.company,
		"due_date": row.due_date,
		"posting_date": row.posting_date,
		frappe.scrub(party_type): row.party,
		"doctype": "Sales Invoice" if self.invoice_type == "Sales" else "Purchase Invoice",
		"currency": frappe.get_cached_value('Company',  self.company,  "default_currency")
	})

	if self.invoice_type == "Sales":
		args["is_pos"] = 0

	return args

@frappe.whitelist()
def get_temporary_opening_account(company=None):
	if not company:
		return

	accounts = frappe.get_all("Account", filters={
		'company': company,
		'account_type': 'Temporary'
	})
	if not accounts:
		frappe.throw(_("Please add a Temporary Opening account in Chart of Accounts"))

	return accounts[0].name