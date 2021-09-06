# Patch In GL Entry for Updating Cost Center in MVTT
data = frappe.get_list("GL Entry",{'company':'Millennium Vitrified Tiles Pvt. Ltd. Testing','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MVTT')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))

# Patch In GL Entry for Updating Cost Center in MVT
data = frappe.get_list("GL Entry",{'company':'Millennium Vitrified Tiles Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MVT')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))

# Patch In GL Entry for Updating Cost Center in MCTT
data = frappe.get_list("GL Entry",{'company':'Millennium Cera Tiles Pvt. Ltd. Testing','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MCTT')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))


# Patch In GL Entry for Updating Cost Center in LVTPL
data = frappe.get_list("GL Entry",{'company':'Lorenzo Vitrified Tiles Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - LVTPL')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))


# Patch In GL Entry for Updating Cost Center in MGI
data = frappe.get_list("GL Entry",{'company':'Maruti Gold Industries','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MGI')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 

# Patch In GL Entry for Updating Cost Center in VF
data = frappe.get_list("GL Entry",{'company':'Victory Floor Tiles Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - VF')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 

# Patch In GL Entry for Updating Cost Center in KC
data = frappe.get_list("GL Entry",{'company':'Koradiya Ceramics Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - KC')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 


query = frappe.db.sql("""
    select pe.name
    from `tabPayment Entry` as pe JOIN
    `tabGL Entry` as gl on gl.voucher_no = pe.name
    where
        gl.voucher_type = 'Payment Entry'
        and (gl.account LIKE '%Debtors%' or gl.account LIKE '%Creditors%')
        and pe.paid_amount * 1.2 < (gl.debit + gl.credit) 
""")

# cost_center Patch
query = frappe.get_list("Purchase Invoice",{'cost_center':['LIKE',''],'docstatus':['!=',2]})
for idx,d in enumerate(query,start=0):
    doc = frappe.get_doc("Purchase Invoice",d.name)
    company_cost_center = frappe.db.get_value("Company",doc.company,'cost_center')
    doc.db_set('cost_center',company_cost_center,update_modified = False)
    if idx % 500 == 0:
        frappe.db.commit()
        print("commited at " + str(idx) + " " + str(d.name))
    print(str(idx) + " "+  str(d.name))


# update transaction_status to new 
query = frappe.db.sql("update `tabSales Invoice` set  transaction_status = 'New' where transaction_status IS NULL")
query = frappe.db.sql("update `tabDelivery Note` set  transaction_status = 'New' where transaction_status IS NULL")
query = frappe.db.sql("select count(name) from `tabGL Entry` where transaction_status IS NULL")

query = frappe.db.sql("update `tabGL Entry` set transaction_status = 'New' where transaction_status IS NULL")


# Patch Start: Change Primary customer Logic
#(in testing company primary customer should be set as customer in DN,SI,PE,JV)

# First Check if company is unauthorized and document is authorized
# For Delivery Note and Sales Invoice
documents_list = ["Delivery Note","Sales Invoice"]
remaining = []
for document in documents_list:
    lst = frappe.db.get_all(document,{"company":"Millennium Vitrified Tiles Pvt. Ltd. Testing","docstatus":1},["name","customer","primary_customer"])
        
    for idx,doc in enumerate(lst):
        if doc.primary_customer and doc.primary_customer != doc.customer:
            frappe.db.set_value(document,doc.name,"customer",doc.primary_customer,update_modified=False)
            frappe.db.set_value(document,doc.name,"customer_name",frappe.db.get_value("Customer",doc.primary_customer,"customer_name"),update_modified=False)
            frappe.db.sql("update `tabGL Entry` set party='{}' where voucher_type='{}' and voucher_no = '{}' and (party != '' or party IS NOT NULL)".format(doc.primary_customer,document,doc.name))

        if idx % 500 == 0:
            frappe.db.commit()

# For Payment Entry

lst = frappe.db.get_all("Payment Entry",{"company":"Millennium Vitrified Tiles Pvt. Ltd. Testing","docstatus":1,"party_type":"Customer"},["name","party","primary_customer"])
document = "Payment Entry"
for idx,doc in enumerate(lst):
    if doc.primary_customer and doc.primary_customer != doc.party:
        frappe.db.set_value(document,doc.name,"party",doc.primary_customer,update_modified=False)
        frappe.db.set_value(document,doc.name,"party_name",frappe.db.get_value("Customer",doc.primary_customer,"customer_name"),update_modified=False)
        frappe.db.sql("update `tabGL Entry` set party='{}' where voucher_type='{}' and voucher_no = '{}' and (party != '' or party IS NOT NULL)".format(doc.primary_customer,document,doc.name))

    if idx % 500 == 0:
        frappe.db.commit()


# For Journal Entry
jv_list = frappe.db.sql("""select jv.name
            from `tabJournal Entry` as jv
            JOIN `tabJournal Entry Account` as jva on jva.parent = jv.name
            where jva.party_type = 'Customer' and jva.party != jv.primary_customer
            and (jv.primary_customer != '' or jv.primary_customer IS NOT NULL)
            and jv.docstatus = 1 and jv.company = 'Millennium Vitrified Tiles Pvt. Ltd. Testing'
            """,as_dict=1)
document = "Journal Entry"

for jv in jv_list:
    doc = frappe.get_doc("Journal Entry",jv)
    if doc.primary_customer:
        for acc in doc.accounts:
            if acc.party_type == 'Customer' and acc.party and acc.party != doc.primary_customer:
                frappe.db.sql("update `tabGL Entry` set party='{}' where voucher_type='Journal Entry' and voucher_no = '{}' and party = '{}' and (party != '' or party IS NOT NULL)".format(doc.primary_customer,doc.name,acc.party))
                acc.db_set('party',doc.primary_customer,update_modified=False)

# Patch End







# Patch Start: Update Pay Amount left in sales invoice
query = frappe.db.sql("""
    update `tabSales Invoice` asi
    JOIN `tabSales Invoice` as si on si.si_ref = asi.name
    set asi.pay_amount_left = asi.real_difference_amount
    where asi.pay_amount_left = 0 and asi.outstanding_amount = asi.real_difference_amount and 
    asi.authority = 'Unauthorized' and asi.outstanding_amount > 0 and asi.real_difference_amount > 0 and si.status = "Paid"
""")

# First Patch

query = frappe.db.sql("""
    update `tabSales Invoice`
    set pay_amount_left = real_difference_amount
    where pay_amount_left  = 0 and outstanding_amount = rounded_total and authority = 'Unauthorized'
""")

# Second Patch

query = frappe.db.sql("""
    update `tabSales Invoice` asi
    JOIN `tabSales Invoice` as si on si.si_ref = asi.name
    set asi.pay_amount_left = asi.real_difference_amount
    where asi.pay_amount_left = 0 and asi.outstanding_amount = asi.real_difference_amount and 
    asi.authority = 'Unauthorized' and asi.outstanding_amount > 0 and asi.real_difference_amount > 0 and si.status = "Paid"
""")

# Patch End