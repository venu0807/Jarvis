from event_bus import get_bus
bus = get_bus()
bus.publish("jobs.test", "jobs.applied", {"company": "Google", "title": "Software Engineer"})
bus.publish("pinterest.test", "pinterest.pin_posted", {"product": "Neon Lamp"})
print("Events published!")
