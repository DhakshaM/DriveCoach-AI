import csv
import bcrypt
from pathlib import Path
# At the top of auth_service.py, add:
from backend.db.db_writer import log_user

USER_FILE = Path("data/users.csv")

def load_users():
    if not USER_FILE.exists():
        return []
    with open(USER_FILE, newline="") as f:
        return list(csv.DictReader(f))

def save_user(user_id, password, role):
    USER_FILE.parent.mkdir(parents=True, exist_ok=True)

    users = load_users()
    if any(u["user_id"] == user_id for u in users):
        return False, "User already exists."

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    write_header = not USER_FILE.exists()
    with open(USER_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["user_id", "password_hash", "role"])
        writer.writerow([user_id, pw_hash, role])
        
    log_user(user_id, role)
    return True, "Signup successful."

def authenticate(user_id, password):
    print("AUTH ATTEMPT:", user_id)
    users = load_users()
    for u in users:
        if u["user_id"] == user_id:
            if bcrypt.checkpw(password.encode(), u["password_hash"].encode()):
                return True, u["role"]
            return False, "Invalid password"
    return False, "User not found"
