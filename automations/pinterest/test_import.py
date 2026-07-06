import sys
import os
sys.path.append(os.path.abspath('/home/venu/Proposals/Jarvis'))
try:
    import event_bus
    print('SUCCESS')
except Exception as e:
    print('ERROR:', e)
