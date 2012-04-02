===================
Worksnaps API
===================

Example::

	from datetime import date
	from pyworksnaps import Worksnaps

	w = Worksnaps('yourtoken')

	for project in w.projects():
		print project.name

		for entry in project.entries(start=date(2012, 3, 1), end=date(2012, 3, 8)):
			print '\t', entry.user.first_name, entry.user.last_name
			if entry.user_comment:
				print '\t\tcomment:',entry.user_comment

