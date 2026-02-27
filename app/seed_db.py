# seed_db.py — run once, then delete
from backend.db.db_writer import log_user
import time

log_user("driver_01", "driver")
log_user("driver_02", "driver")
log_user("driver_03", "driver")
log_user("coach_01", "coach")

time.sleep(2)   # give background thread time to flush
print("Done seeding users into DB.")