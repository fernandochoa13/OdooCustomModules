# -*- coding: utf-8 -*-

from . import test_property
from . import test_pms_projects
from . import test_pms_projects_routes
from . import test_material_orders


# cd "C:\Program Files\Odoo 16.0e.20230912\server"
# python odoo-bin -d BackupDB -c odoo.conf --test-file=odoo/addons/pms/tests/test_investments.py

# upgrades

# python odoo-bin -d BackupDB -c odoo.conf -u account_reports 