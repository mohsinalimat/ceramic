import frappe
from frappe import _

def on_submit(self, test):
    """On Submit Custom Function for Sales Invoice"""
    create_main_sales_invoice(self)

def create_main_sales_invoice(self):
    si = frappe.new_doc("Sales Invoice")
    
    si.posting_date = self.posting_date
    si.posting_time = self.posting_time
    si.set_posting_time = self.set_posting_time
    si.address_display = self.address_display
    si.company = frappe.db.get_value("Company", self.company, "alternate_company") or si.company
	si.customer = self.customer or "_Test Customer"
	# si.debit_to = args.debit_to or "Debtors - _TC"
	# si.update_stock = args.update_stock
	si.is_pos = self.is_pos
	si.is_return = self.is_return
	si.return_against = self.return_against
	si.currency = self.currency or "INR"
	si.conversion_rate = self.conversion_rate or 1
    
    dn_doc = frappe.get_doc("Delivery Note", "")

    for index, item in enumerate(self.items):
        si.append('items', {
            "item_code": item.item_code,
            "gst_hsn_code": item.gst_hsn_code,
            "warehouse": item.warehouse or '',
            "qty": item.qty,
            "rate": item.rate,
            "income_account": item.income_account,
            "expense_account": item.expense_account,
            "cost_center": item.cost_center,
            "serial_no": item.serial_no
        })
    
    si.save()
    


def create_purchase_invoice(self):
    pi = frappe.new_doc("Purchase Invoice")

    pi.naming_series = db.get_value("Company", self.customer, 'purchase_invoice')
    pi.company = self.customer
    pi.supplier = self.company
    pi.due_date = self.due_date
    pi.bill_no = self.name
    pi.bill_date = self.posting_date
    pi.currency = self.currency
    pi.update_stock = self.update_stock

    for item in self.items:
        pi.append('items', {
            'item_code': item.item_code,
            'item_name': item.item_name,
            'qty': item.qty,
            'rate': item.rate,
            'description': item.description,
            'uom': item.uom,
            'price_list_rate': item.price_list_rate,
            'rate': item.rate,
            'original_rate': item.original_rate,
            'discount_per': item.discount_per,
            'purchase_order': frappe.db.get_value("Purchase Order Item", item.purchase_order_item, 'parent'),
            'po_detail': item.purchase_order_item
        })

    pi.taxes_and_charges = self.taxes_and_charges
    pi.shipping_rule = self.shipping_rule
    pi.shipping_address = self.shipping_address_name
    pi.shipping_address_display = self.shipping_address
    pi.tc_name = 'Purchase Terms'

    old_abbr = db.get_value("Company", self.company, 'abbr')
    new_abbr = db.get_value("Company", self.customer, 'abbr')

    for tax in self.taxes:
        account_head = tax.account_head.replace(old_abbr, new_abbr)
        if not db.exists("Account", account_head):
            frappe.msgprint(_("The Account Head <b>{0}</b> does not exists. Please create Account Head for company <b>{1}</b> and create Purchase Invoice manually.".format(_(account_head), _(self.customer))), title="Purchase Invoice could not be created", indicator='red')
            return

        pi.append('taxes',{
            'charge_type': tax.charge_type,
            'row_id': tax.row_id,
            'account_head': account_head,
            'description': tax.description.replace(old_abbr, ''),
            'rate': tax.rate,
            'tax_amount': tax.tax_amount,
            'total': tax.total
        })

    pi.save()
    self.db_set('purchase_invoice', pi.name)
    pi.submit()
    db.commit()

    url = get_url_to_form("Purchase Invoice", pi.name)
    frappe.msgprint(_("Purchase Invoice <b><a href='{url}'>{name}</a></b> has been created successfully!".format(url=url, name=pi.name)), title="Purchase Invoice Created", indicator="green")
