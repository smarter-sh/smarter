
mysql -u ${mysql_user} --password="${mysql_password}" --host "${mysql_host}" --port ${mysql_port} -e "CREATE DATABASE IF NOT EXISTS ${mysql_database};"
mysql -u ${mysql_user} --password="${mysql_password}" --host "${mysql_host}" --port ${mysql_port} -e "CREATE USER IF NOT EXISTS '${smarter_mysql_user}'@'%' IDENTIFIED BY '${smarter_mysql_password}';"
mysql -u ${mysql_user} --password="${mysql_password}" --host "${mysql_host}" --port ${mysql_port} -e "GRANT ALL PRIVILEGES ON ${mysql_database}.* TO '${smarter_mysql_user}'@'%'; FLUSH PRIVILEGES;"
python manage.py migrate
python manage.py create_user --username ${admin_username} --email ${admin_email} --password ${admin_password} --admin
