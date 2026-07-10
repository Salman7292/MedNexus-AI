import sqlite3

def clean_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # 1. Fetch all users
    users = c.execute('SELECT id, username FROM users').fetchall()
    
    # 2. Lowercase usernames and identify duplicates to delete
    seen_emails = {}
    ids_to_delete = []
    
    # Sort by ID so we keep the oldest account
    for user_id, username in sorted(users, key=lambda x: x[0]):
        lower_email = username.strip().lower()
        if lower_email in seen_emails:
            # We already have an account for this email, mark this one for deletion
            ids_to_delete.append(user_id)
        else:
            seen_emails[lower_email] = user_id
            # Update to lowercase if it wasn't already
            if username != lower_email:
                c.execute('UPDATE users SET username = ? WHERE id = ?', (lower_email, user_id))
    
    # 3. Delete duplicate accounts
    if ids_to_delete:
        print(f"Found {len(ids_to_delete)} duplicate accounts. Deleting...")
        c.execute(f"DELETE FROM users WHERE id IN ({','.join('?' * len(ids_to_delete))})", ids_to_delete)
        
    # 4. Migrate to a new table with a UNIQUE constraint
    # We rename the old, create the new, copy, and drop
    c.execute('ALTER TABLE users RENAME TO users_old')
    
    c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            full_name TEXT,
            profile_pic TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        INSERT INTO users (id, username, password_hash, full_name, profile_pic, created_at)
        SELECT id, username, password_hash, full_name, profile_pic, created_at FROM users_old
    ''')
    
    c.execute('DROP TABLE users_old')
    
    conn.commit()
    conn.close()
    print("Database cleaned and UNIQUE constraint applied to 'username' column.")

if __name__ == "__main__":
    clean_database()
