import sys

path = '/var/www/xzakox/public_html/test/'
if path not in sys.path:
	sys.path.append(path)
from tracker import app as application
