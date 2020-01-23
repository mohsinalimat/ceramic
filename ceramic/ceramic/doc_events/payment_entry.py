import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

def on_submit(self, test):
    """On Submit Custom Function for Sales Invoice"""
    create_main_payment_entry(self)

def on_cancel(self, test):
    """On Cancel Custom Function for Sales Invoice"""
    cancel_payment_entry(self)

def on_trash(self, test):
    delete_payment_entry(self)

def create_main_payment_entry(self):
    authority = frappe.db.get_value("Company", self.company, "authority")

    def get_payment_entry_entry(source_name, target_doc=None, ignore_permissions= True):
        def set_missing_values(source, target):
            target_company = frappe.db.get_value("Company", source.company, "alternate_company")
            target.company = target_company
            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

            target.paid_from = source.paid_from.replace(source_company_abbr, target_company_abbr)
            target.paid_to = source.paid_to.replace(source_company_abbr, target_company_abbr)
            
            # target.ref_payment = self.name

            if source.deductions:
                for index, i in enumerate(source.deductions):
                    target.deductions[index].account.replace(source_company_abbr, target_company_abbr)
                    target.deductions[index].cost_center.replace(source_company_abbr, target_company_abbr)

            # frappe.throw("Hulalalal")
            # frappe.throw(str(target.deductions[0]))
            # target.set_missing_values()
            

        def payment_ref(source_doc, target_doc, source_parent):
            reference_name = source_doc.reference_name
            target_doc.reference_name = frappe.db.get_value("Sales Invoice", reference_name, 'ref_invoice')

        fields = {
            "Payment Entry": {
                "doctype": "Payment Entry",
                "field_map": {},
                "field_no_map": {
                    "party_balance",
                    "paid_to_account_balance",
                    "status",
                    "letter_head",
                    "print_heading",
                    "bank",
                    "bank_account_no",
                    "remarks",
                    "authority",
                },
            },
            "Payment Entry Reference": {
                "doctype": "Payment Entry Reference",
                "field_map": {},
                "field_no_map": {},
                "postprocess": payment_ref,
            }
        }

        doclist = get_mapped_doc(
            "Payment Entry",
            source_name,
            fields,
            target_doc,
            set_missing_values,
            ignore_permissions=ignore_permissions
        )

        return doclist
    
    if authority == "Authorized":
        pe = get_payment_entry_entry(self.name)
        try:
            pe.save(ignore_permissions= True)
            self.db_set('ref_payment', pe.name)
            frappe.db.commit()
            pe.submit()
        except Exception as e:
            frappe.db.rollback()
            frappe.throw(e)

# Cancel Invoice on Cancel
def cancel_payment_entry(self):
    if self.ref_payment:
        pe = frappe.get_doc("Payment Entry", {'ref_payment':self.name})
    else:
        pe = None
    
    if pe:
        if pe.docstatus == 1:
            pe.flags.ignore_permissions = True
            try:
                pe.cancel()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)

def delete_payment_entry(self):
    ref_name = self.ref_payment
    try:
        frappe.db.set_value("Payment Entry", self.name, 'ref_payment', '')    
        frappe.db.set_value("Payment Entry", ref_name, 'ref_payment', '')
        frappe.delete_doc("Payment Entry", ref_name, force = 1)
    except Exception as e:
        frappe.db.rollback()
        frappe.throw(e)
    else:
        frappe.db.commit()

    