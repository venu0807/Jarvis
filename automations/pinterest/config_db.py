with open('/etc/postgresql/18/main/postgresql.conf', 'a') as f:
    f.write('\nlisten_addresses = \'*\'\n')
with open('/etc/postgresql/18/main/pg_hba.conf', 'a') as f:
    f.write('\nhost all all 127.0.0.1/32 trust\n')
