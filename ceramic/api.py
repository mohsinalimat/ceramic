import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, cstr, getdate
from frappe.model.mapper import get_mapped_doc

def check_sub(string, sub_str): 
	if (string.find(sub_str) == -1): 
	   return False 
	else: 
		return True

def naming_series_name(name, company_series):
	
	if check_sub(name, '.fiscal.'):
		current_fiscal = frappe.db.get_value('Global Defaults', None, 'current_fiscal_year')
		fiscal = frappe.db.get_value("Fiscal Year", str(current_fiscal),'fiscal')
		name = name.replace('.fiscal.', str(fiscal))

	if check_sub(name, '.YYYY.'):
		name = name.replace('.YYYY.', '.2020.')

	if company_series:
		if check_sub(name, 'company_series.'):
			name = name.replace('company_series.', str(company_series))
			
	if check_sub(name, ".#"):
		name = name.replace('#', '')
		if name[-1] == '.':
			name = name[:-1]
	
	return name

@frappe.whitelist()
def docs_before_naming(self, method):
	from erpnext.accounts.utils import get_fiscal_year

	date = self.get("transaction_date") or self.get("posting_date") or getdate()

	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	if fiscal:
		self.fiscal = fiscal
	else:
		fy_years = fy.split("-")
		fiscal = fy_years[0][2:] + "-" + fy_years[1][2:]
		self.fiscal = fiscal

@frappe.whitelist()
def check_counter_series(name = None, company_series = None):
	name = naming_series_name(name, company_series)
	
	check = frappe.db.get_value('Series', name, 'current', order_by="name")
	
	if check == 0:
		return 1
	elif check == None:
		frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
		return 1
	else:
		return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1


@frappe.whitelist()
def before_naming(self, method):
	if not self.amended_from:
		if self.series_value:
			if self.series_value > 0:
				name = naming_series_name(self.naming_series, self.company_series)
				
				check = frappe.db.get_value('Series', name, 'current', order_by="name")
				if check == 0:
					pass
				elif not check:
					frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
				
				frappe.db.sql(f"update `tabSeries` set current = {int(self.series_value) - 1} where name = '{name}'")
		
@frappe.whitelist()
def get_party_details(party=None, party_type=None, ignore_permissions=True):

	if not party:
		return {}

	if not frappe.db.exists(party_type, party):
		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))

	return _get_party_details(party, party_type, ignore_permissions)

def _get_party_details(party=None, party_type=None, ignore_permissions=True):

	out = frappe._dict({
		party_type.lower(): party
	})

	party = out[party_type.lower()]

	# if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
	# 	frappe.throw(_("Not permitted for {0}").format(party), frappe.PermissionError)

	party = frappe.get_doc(party_type, party)
	
	# set_address_details(out, party, party_type)
	# set_contact_details(out, party, party_type)
	# set_other_values(out, party, party_type)
	set_organization_details(out, party, party_type)
	return out
		
def set_organization_details(out, party, party_type):

	organization = None

	if party_type == 'Lead':
		organization = frappe.db.get_value("Lead", {"name": party.name}, "company_name")
	elif party_type == 'Customer':
		organization = frappe.db.get_value("Customer", {"name": party.name}, "customer_name")
	elif party_type == 'Supplier':
		organization = frappe.db.get_value("Supplier", {"name": party.name}, "supplier_name")

	out.update({'party_name': organization})


@frappe.whitelist()
def restrict_access():
	role_permission_list = frappe.get_all("User Permission", filters = {
		"allow": "Authority", "for_value": "Unauthorized"
	}, fields = ['name', 'system_genrated'], ignore_permissions = True)
	for item in role_permission_list:
		if not item['system_genrated']:
			doc = get_mapped_doc("User Permission", item['name'], {
				"User Permission": {
					"doctype": "Backup User Permission",
				}
			}, ignore_permissions = True)

			try:
				doc.save(ignore_permissions = True)
			except:
				pass
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)
	
	user_list = frappe.get_all("User", filters = {'enabled': 1}, fields = ['email', 'username'], ignore_permissions = True)
	for user in user_list:
		if user['username'] != 'administrator' and user['email'] != 'guest@example.com':
			
			if not frappe.db.exists({
				'doctype': 'User Permission',
				'user': user['email'],
				'allow': 'Authority',
				'for_value': 'Authorized'
			}):
				doc = frappe.new_doc("User Permission")

				doc.user = user['email']
				doc.allow = 'Authority'
				doc.for_value = 'Authorized'
				doc.apply_to_all_doctypes = 1
				doc.system_genrated = 1

				try:
					doc.save(ignore_permissions = True)
				except:
					pass
	frappe.db.set_value("Global Defaults", "Global Defaults", "restricted_access", 1)
	frappe.db.commit()
	# frappe.msgprint("Restricted Access")
	return "success"

@frappe.whitelist()
def reverse_restrict_access():
	permission_list = frappe.get_all("Backup User Permission")
	for item in permission_list:
		print(item['name'])
		doc = get_mapped_doc("Backup User Permission", item['name'], {
			"Backup User Permission": {
				"doctype": "User Permission",
			}
		})

		doc.save()
		
		frappe.delete_doc("Backup User Permission", item['name'], ignore_permissions = True)
	
	user_permission_list = frappe.get_all("User Permission", filters = {'system_genrated': 1})

	for item in user_permission_list:
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)

	frappe.set_value("Global Defaults", "Global Defaults", "restricted_access", 0)
	frappe.db.commit()

	frappe.msgprint("All Permission Reversed")

@frappe.whitelist()
@frappe.read_only()
def get_open_count(doctype, name, items=[]):
	'''Get open count for given transactions and filters

	:param doctype: Reference DocType
	:param name: Reference Name
	:param transactions: List of transactions (json/dict)
	:param filters: optional filters (json/list)'''

	if frappe.flags.in_migrate or frappe.flags.in_install:
		return {
			"count": []
		}

	frappe.has_permission(doc=frappe.get_doc(doctype, name), throw=True)

	meta = frappe.get_meta(doctype)
	links = meta.get_dashboard_data()

	# compile all items in a list
	if not items:
		for group in links.transactions:
			items.extend(group.get("items"))

	if not isinstance(items, list):
		items = json.loads(items)

	out = []
	for d in items:
		if d in links.get("internal_links", {}):
			# internal link
			continue

		filters = get_filters_for(d)
		fieldname = links.get("non_standard_fieldnames", {}).get(d, links.fieldname)
		data = {"name": d}
		if filters:
			# get the fieldname for the current document
			# we only need open documents related to the current document
			filters[fieldname] = name
			total = len(frappe.get_list(d, fields="name",
				filters=filters, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
			data["open_count"] = total

		total = len(frappe.get_list(d, fields="name",
			filters={fieldname: name}, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
		data["count"] = total
		out.append(data)

	out = {
		"count": out,
	}

	module = frappe.get_meta_module(doctype)
	if hasattr(module, "get_timeline_data"):
		out["timeline_data"] = module.get_timeline_data(doctype, name)

	return out

def item_patch():
	data = frappe.db.sql("SELECT * FROM `tabItem` WHERE is_tile = 1 and tile_quality = 'Premium' AND is_item_series = 0", as_dict = 1)
	tile_categries = ['Premium', 'Golden', 'Economy', 'Classic']

	for item in data:
		if not frappe.db.exists("Tile Item Creation Tool", item.item_name.replace("-Premium", '')):
			tile_item = frappe.new_doc("Tile Item Creation Tool")
			tile_item.item_name = item.item_name.replace("-Premium", '')
		else:
			tile_item = frappe.get_doc("Tile Item Creation Tool", item.item_name.replace("-Premium", ''))
			if tile_item.docstatus == 1:
				continue
		tile_item.item_series = item.item_series
		tile_item.item_group = item.item_group
		tile_item.item_design = item.item_design
		
		tile_item.tile_quality = []
		tile_item.default_production_price = 0

		tile_item.image = item.image
		tile_item.cover_image = item.cover_image

		for j in tile_categries:
			item_name = item.item_name.replace('Premium', j)
			item_doc = frappe.get_doc('Item', {'item_name': item_name})
			item_doc.db_set("item_creation_tool", tile_item.item_name)

			tile_item.append('tile_quality', {
				'tile_quality': j,
				'item_code': item_doc.item_code,
				'production_price': 0
			})


			tile_item.item_defaults = []
			for k in item_doc.item_defaults:
				tile_item.append('item_defaults', {
					'company': k.company,
					'default_warehouse': k.default_warehouse,
				})
			
			if item_doc.show_in_website:
				tile_item.show_in_website = 1
				tile_item.weightage = item_doc.weightage
				tile_item.slideshow = item.slideshow
				tile_item.website_warehouse = item.website_warehouse
				tile_item.website_image = item.website_image
		lst = []
		
		for k in tile_item.tile_quality:
			if k.tile_quality:
				lst.append(k)

		tile_item.tile_quality = []
		tile_item.tile_quality = lst
			
		tile_item.save()
		
		frappe.db.commit()
		
		print(tile_item.item_name)

def tile_item_creation_update():
	data = frappe.get_all("Tile Item Creation Tool")

	for item in data:
		doc = frappe.get_doc("Tile Item Creation Tool", item.name)

		doc.item_defaults = []

		doc.append('item_defaults', {
			'company': 'Millennium Vitrified Tiles Pvt. Ltd. Testing',
			'default_warehouse': 'Stores - MVTT'
		})

		for tile in doc.tile_quality:
			item_price = frappe.get_doc("Item Price", {'item_code': tile.item_code})
			
			tile.production_price = item_price.price_list_rate
			doc.default_production_price = item_price.price_list_rate

		doc.save()
		frappe.db.commit()
		print(doc.name)
