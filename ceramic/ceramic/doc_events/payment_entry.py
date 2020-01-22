import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

def on_submit(self, test):
    """On Submit Custom Function for Sales Invoice"""
    create_main_payment_entry(self)

def create_main_payment_entry(self):
    authority = frappe.db.get_value("Company", self.company, "authority")

    def get_payment_entry_entry(source_name, target_doc=None, ignore_permissions= True):
        def set_target_values(source, target):
            target_company = frappe.db.get_value("Company", source.company, "alternate_company")
            target.company = target_company
            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

            target.ref_invoice = self.name

            if source.debit_to:
                target.debit_to = source.debit_to.replace(source_company_abbr, target_company_abbr)
            if source.taxes_and_charges:
                target.taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)

                for index, i in enumerate(source.taxes):
                    target.taxes[index].charge_type = "Actual"
                    target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)

            if self.amended_from:
                name = frappe.db.get_value("Sales Invoice", {"ref_invoice": source.amended_from}, "name")
                target.amended_from = name

            target.set_missing_values()

        def payment_details(source_doc, target_doc, source_parent):
            reference_name = source_doc.reference_name
            target_doc.reference_name = frappe.db.get_value("Sales Invoice", reference_name, 'ref_invoice')

        fields = {
            "Payment Entry": {
                "doctype": "Payment Entry",
                "field_map": {},
                "field_no_map": {
                    "party_balance",
                    "paid_to",
                    "paid_from",
                    "paid_to_account_currency",
                    "paid_from_account_currency",
                    "paid_from_account_currency",
                    "paid_to_account_balance",
                },
            },
            "Payment Entry Reference": {
                "doctype": "Payment Entry Reference",
                "field_map": {},
                "field_no_map": {},
                "postprocess": payment_details,
            }
        }

        doclist = get_mapped_doc(
            "Payment Entry",
            source_name,
            fields, target_doc,
            set_target_values,
            ignore_permissions=ignore_permissions
        )

        return doclist
    
     if authority == "Authorized":
        pe = get_sales_invoice_entry(self.name)
        try:
            pe.save()
            self.db_set('ref_invoice', si.name)
            frappe.db.commit()
            pe.submit()
        except Exception as e:
            frappe.db.rollback()
            frappe.throw(e)