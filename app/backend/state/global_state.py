import time
from threading import Lock

current_user_id = None
current_role = None


class GlobalState:
    def __init__(self):
        self.active_drivers = {}
        self.lock = Lock()

    def driver_login(self, driver_id, name=None):
        with self.lock:
            print(">>> DRIVER LOGIN:", driver_id)
            self.active_drivers[driver_id] = {
                "name": name or driver_id
            }
            print(">>> ACTIVE DRIVERS NOW:", self.active_drivers)


    def get_driver_status(self, driver_id):
        with self.lock:
            return {
                "driver_id": driver_id,
                "online": driver_id in self.active_drivers
            }
    
    def driver_login(self, driver_id, name=None):
        print(">>> DRIVER LOGIN:", driver_id)
        self.active_drivers[driver_id] = {
            "name": name or driver_id
        }
        print(">>> ACTIVE DRIVERS NOW:", self.active_drivers)

    def driver_logout(self, driver_id):
        with self.lock:
            print(">>> DRIVER LOGOUT:", driver_id)
            self.active_drivers.pop(driver_id, None)
            print(">>> ACTIVE DRIVERS NOW:", self.active_drivers)

GLOBAL_STATE = GlobalState()
