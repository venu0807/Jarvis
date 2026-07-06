#!/bin/bash
su - postgres -c '/usr/lib/postgresql/18/bin/pg_ctl -D /var/lib/postgresql/18/main -o "-c config_file=/etc/postgresql/18/main/postgresql.conf" start'
sleep infinity
