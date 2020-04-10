from __future__ import unicode_literals
from frappe import _

def get_data(data):
	data['transactions'] = []
	return data