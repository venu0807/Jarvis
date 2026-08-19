#!/bin/bash
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/18/main/postgresql.conf
echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/18/main/pg_hba.conf
echo "host all all ::0/0 trust" >> /etc/postgresql/18/main/pg_hba.conf
service postgresql restart
