import frappe

def before_save(self,method):
	start_date = str(self.year_start_date)
	end_date = str(self.year_end_date)

	fiscal = start_date.split("-")[0][2:] + end_date.split("-")[0][2:]
	self.fiscal = fiscal