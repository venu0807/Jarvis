#!/usr/bin/env python3
import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
from automations.alert_triggers import main
result = main()
print(f"Result: {result}")