# Settings package — import from base, then environment-specific overlay.
try:
    import pymysql
except ModuleNotFoundError:
    pymysql = None
else:
    pymysql.install_as_MySQLdb()
