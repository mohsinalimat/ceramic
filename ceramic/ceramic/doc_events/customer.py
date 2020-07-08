import frappe
from frappe import _

from erpnext.accounts.party import validate_party_accounts

def customer_validate(self):
	self.flags.is_new_doc = self.is_new()
	self.flags.old_lead = self.lead_name
	validate_party_accounts(self)
	self.validate_credit_limit_on_change()
	self.set_loyalty_program()
	self.check_customer_group_change()
	self.validate_default_bank_account()

	# set loyalty program tier
	if frappe.db.exists('Customer', self.name):
		customer = frappe.get_doc('Customer', self.name)
		if self.loyalty_program == customer.loyalty_program and not self.loyalty_program_tier:
			self.loyalty_program_tier = customer.loyalty_program_tier

def before_validate(self, method):
	from erpnext.selling.doctype.customer.customer import Customer
	Customer.validate = customer_validate

def validate(self, method):
	if self.is_primary_customer:
		self.primary_customer = self.name or self.customer_name