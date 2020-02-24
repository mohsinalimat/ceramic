import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


def before_save(self, method):
    """On Submit Custom Function for Sales Invoice"""
    create_cost_center(self)


def create_cost_center(self):
    if self.company:

        # Getting authority of company
        authority = frappe.db.get_value("Company", self.company, "authority")

        if authority == "Authorized":
            target_company = frappe.db.get_value("Company", self.company, "alternate_company")
            
            cc = frappe.new_doc("Cost Center")

            cc.cost_center_name = self.cost_center_name
            cc.company = frappe.db.get_value("Company", self.company, "alternate_company")

            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")

            if self.parent_cost_center:
                cc.parent_cost_center = self.parent_cost_center.replace(self.company, cc.company).replace(source_company_abbr, target_company_abbr)
            
            if self.is_group:
                cc.is_group = self.is_group

            if self.disabled:
                cc.disabled = s.disabled
        
            try:
                cc.save()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)
            