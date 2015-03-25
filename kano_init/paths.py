#
# Path constants
#
# Copyright (C) 2015 Kano Computing Ltd.
# License: http://www.gnu.org/licenses/gpl-2.0.txt GNU GPL v2
#

import os

STATUS_FILE_PATH = '/var/cache/kano-init/status.json'

PACKAGE_PATH = os.path.dirname(__file__)
DATA_PATH = os.path.join(PACKAGE_PATH, 'data')

SUBSHELLRC_PATH = os.path.join(DATA_PATH, 'subshellrc')
