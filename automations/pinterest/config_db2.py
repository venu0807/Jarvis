with open('/etc/postgresql/18/main/postgresql.conf', 'a') as f:
    f.write('\nunix_socket_directories = \'/tmp\'\n')
