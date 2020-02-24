import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


def before_save(self, method):
    """On Submit Custom Function for Sales Invoice"""
    account(self)

def account(self):
    if self.company:

        # Getting authority of company
        authority = frappe.db.get_value("Company", self.company, "authority")

        if authority == "Authorized":
            target_company = frappe.db.get_value("Company", self.company, "alternate_company")
            
            if frappe.db.exists("Account", {"company": target_company, "account_name": self.account_name}):
                coa = frappe.get_doc("Account", {"company": target_company, "account_name": self.account_name})
                coa.freeze_account = self.freeze_account
            else:
                coa = frappe.new_doc("Account")
                coa.account_name = self.account_name
                coa.company = frappe.db.get_value("Company", self.company, "alternate_company")
                coa.freeze_account = 'No'

            
            coa.account_currency = self.account_currency
            coa.account_type = self.account_type

            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")

            if self.parent_account:
                coa.parent_account = self.parent_account.replace(source_company_abbr, target_company_abbr)
            
            coa.freeze_account = self.is_group
            coa.balance_must_be = self.balance_must_be
            coa.report_type = self.report_type
            coa.root_type = self.root_type
            
            if self.disabled:
                coa.disabled = s.disabled

            try:
                coa.save()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)