import frappe
from frappe import _
from frappe.utils import cint

def before_naming(self, method):
	from erpnext.manufacturing.doctype.bom.bom import BOM
	BOM.autoname = autoname

def before_validate(self, method):
	from erpnext.manufacturing.doctype.bom.bom import BOM
	BOM.validate_main_item = validate_main_item

def before_submit(self, method):
	from erpnext.manufacturing.doctype.bom.bom import BOM
	BOM.manage_default_bom = manage_default_bom

def before_update_after_submit(self, method):
	from erpnext.manufacturing.doctype.bom.bom import BOM
	BOM.manage_default_bom = manage_default_bom

def before_cancel(self, method):
	from erpnext.manufacturing.doctype.bom.bom import BOM
	BOM.manage_default_bom = manage_default_bom

def validate_main_item(self):
	""" Validate main FG item"""
	if self.item:
		item = self.get_item_det(self.item)
		
		if not item:
			frappe.throw(_("Item {0} does not exist in the system or has expired").format(self.item))
		else:
			
			ret = frappe.db.get_value("Item", self.item, ["description", "stock_uom", "item_name"])
			self.description = ret[0]
			self.uom = ret[1]
			self.item_name= ret[2]

	if not self.quantity:
		frappe.throw(_("Quantity should be greater than 0"))

def autoname(self):
	if self.item:
		names = frappe.db.sql_list("""select name from `tabBOM` where item=%s""", self.item)
	else:
		names = frappe.db.sql_list("""select name from `tabBOM` where item_group=%s""", self.item_group)

	if names and self.item:
		# name can be BOM/ITEM/001, BOM/ITEM/001-1, BOM-ITEM-001, BOM-ITEM-001-1

		# split by item
		names = [name.split(self.item, 1) for name in names]
		names = [d[-1][1:] for d in filter(lambda x: len(x) > 1 and x[-1], names)]

		# split by (-) if cancelled
		if names:
			names = [cint(name.split('-')[-1]) for name in names]
			idx = max(names) + 1
		else:
			idx = 1
	elif names and self.item_group:
		# name can be BOM/ITEM/001, BOM/ITEM/001-1, BOM-ITEM-001, BOM-ITEM-001-1

		# split by item
		names = [name.split(self.item_group, 1) for name in names]
		names = [d[-1][1:] for d in filter(lambda x: len(x) > 1 and x[-1], names)]

		# split by (-) if cancelled
		if names:
			names = [cint(name.split('-')[-1]) for name in names]
			idx = max(names) + 1
		else:
			idx = 1
	else:
		idx = 1

	name = 'BOM-' + (self.item or self.item_group) + ('-%.2i' % idx)
	if frappe.db.exists("BOM", name):
		conflicting_bom = frappe.get_doc("BOM", name)

		if conflicting_bom.item != self.item:

			frappe.throw(_("""A BOM with name {0} already exists for item {1}.
				<br> Did you rename the item? Please contact Administrator / Tech support
			""").format(frappe.bold(name), frappe.bold(conflicting_bom.item)))

	self.name = name

def manage_default_bom(self):
	""" Uncheck others if current one is selected as default or
		check the current one as default if it the only bom for the selected item,
		update default bom in item master
	"""
	if self.item:
		if self.is_default and self.is_active:
			from frappe.model.utils import set_default
			set_default(self, "item")
			
			item = frappe.get_doc("Item", self.item)
			if item.default_bom != self.name:
				frappe.db.set_value('Item', self.item, 'default_bom', self.name)
		elif not frappe.db.exists(dict(doctype='BOM', docstatus=1, item=self.item, is_default=1)) \
			and self.is_active:
			frappe.db.set(self, "is_default", 1)
		else:
			frappe.db.set(self, "is_default", 0)
			item = frappe.get_doc("Item", self.item)
			if item.default_bom == self.name:
				frappe.db.set_value('Item', self.item, 'default_bom', None)
	else:
		if self.is_default and self.is_active:
			frappe.db.sql(f"""
				UPDATE `tabBOM` set `is_default` = 0
				WHERE name != '{self.name}' AND `item_group` = '{self.item_group}' AND `item` IS NULL
			""")
			
			item = frappe.get_doc("Item Group", self.item_group)
			if item.default_bom != self.name:
				frappe.db.set_value('Item Group', self.item_group, 'default_bom', self.name)
		elif not frappe.db.exists(dict(doctype='BOM', docstatus=1, item_group=self.item_group, item=None, is_default=1)) \
			and self.is_active:
			frappe.db.set(self, "is_default", 1)
		else:
			frappe.db.set(self, "is_default", 0)
			item = frappe.get_doc("Item Group", self.item_group)
			if item.default_bom == self.name:
				frappe.db.set_value('Item', self.item_group, 'default_bom', None)