import frappe
from frappe import _

def validate(self,method):
	validate_customer_group(self)
	validate_phone(self)

def validate_customer_group(self):
	if self.customer_group:
		if frappe.db.get_value("Customer Group",self.customer_group,'is_group'):
			frappe.throw(_("Please select proper customer group"))
	if self.territory:
		if frappe.db.get_value("Territory",self.territory,'is_group'):
			frappe.throw(_("Please select proper territory"))

def validate_phone(self):
	if self.phone:
		#frappe.throw(len(self.phone))
		number = self.phone[:3]
		if number != '+91':
			frappe.throw("Enter valid mobile number")
		#frappe.throw(str(len(self.phone)))
		if str(len(self.phone)) != '13':
			frappe.throw("Enter valid number")