from __future__ import unicode_literals
from frappe import _

def get_data(data):
	data['non_standard_fieldnames'] =  {
		'Stock Entry': 'delivery_note_no',
		'Auto Repeat': 'reference_document',
	}

	data['transactions'] = [
		{
			'label': _('Related'),
			'items': ['Sales Invoice']
		},
		{
			'label': _('Reference'),
			'items': ['Sales Order']
		},
		{
			'label': _('Returns'),
			'items': ['Stock Entry']
		},
		{
			'label': _('Subscription'),
			'items': ['Auto Repeat']
		},
	]

	return data