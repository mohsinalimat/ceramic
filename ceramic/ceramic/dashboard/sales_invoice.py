from __future__ import unicode_literals
from frappe import _

def get_data(data):
	data['transactions'] = [
		{
			'label': _('Payment'),
			'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
		},
		{
			'label': _('Reference'),
			'items': ['Delivery Note', 'Sales Order']
		},
		{
			'label': _('Returns'),
			'items': ['Sales Invoice']
		},
		{
			'label': _('Subscription'),
			'items': ['Auto Repeat']
		},
	]

	return data