import frappe
from frappe import _
from frappe.utils import cint

def validate(self,method):
    validate_contact_number(self)

def validate_contact_number(self):
    if self.get('phone_nos'):
        for contact in self.phone_nos:
            if contact.phone:
                if not contact.phone[1:].isdigit():
                    frappe.throw('Please Enter Digits only')
                if contact.phone[0] != '+':
                    frappe.throw("Please Enter '+' Sign")
                if len(contact.phone[1:]) != 12:
                    frappe.throw('Please Enter Correct Phone Number')