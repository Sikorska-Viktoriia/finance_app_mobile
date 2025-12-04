import sqlite3
import hashlib
from datetime import datetime, timedelta
import re
import os
import json
import shutil 
import traceback
from kivy.utils import platform
from kivy.resources import resource_find 

# --- КОНСТАНТИ ---
DB_NAME = "users.db"
SALT = "flamingo_secure_salt_2024"

# Глобальні змінні
conn = None
cursor = None

# --- ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ ШЛЯХІВ ---

def _get_android_storage_path(db_name):
    """Отримати надійний шлях для запису БД на Android."""
    try:
        # Імпортуємо тут, щоб уникнути проблем із Buildozer
        from android.storage import app_storage_path
        db_dir = app_storage_path()
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        return os.path.join(db_dir, db_name)
    except ImportError:
        # Резервний шлях для комп'ютера або невдалого імпорту
        return os.path.join(os.path.expanduser('~'), db_name)

def get_db_path():
    """Повертає абсолютний шлях до робочої бази даних."""
    if platform == 'android':
        return _get_android_storage_path(DB_NAME)
    else:
        # Для ПК шлях залишається у корені проєкту
        return DB_NAME

# --- ФУНКЦІЇ БЕЗПЕКИ ТА ВАЛІДАЦІЇ ---

def hash_password(password):
    return hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        SALT.encode('utf-8'), 
        100000
    ).hex()

def check_password(password, hashed):
    try:
        return hash_password(password) == hashed
    except:
        return False

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    return len(password) >= 6
    
def safe_color_conversion(color):
    """Safely convert color string to list"""
    if isinstance(color, list):
        return color
    elif isinstance(color, str):
        try:
            return json.loads(color.replace("'", '"'))
        except:
            try:
                return eval(color) 
            except:
                return [0.2, 0.4, 0.8, 1]
    return [0.2, 0.4, 0.8, 1]

# --- СТРУКТУРА ТА СХЕМА БД ---

def create_db_schema(cursor):
    """Створює всі таблиці, якщо вони не існують."""
    
    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Wallets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 3. User cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            number TEXT NOT NULL,
            bank TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            color TEXT DEFAULT '[0.2, 0.4, 0.8, 1]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 4. Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            card_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (card_id) REFERENCES user_cards (id)
        )
    ''')

    # 5. Savings plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            deadline DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 6. Savings transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (plan_id) REFERENCES savings_plans (id)
        )
    ''')
    
    # 7. Envelopes (categories) table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS envelopes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '[0.2, 0.4, 0.8, 1]',
            budget_limit REAL DEFAULT 0.0,
            current_amount REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 8. Envelope transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS envelope_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            envelope_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            card_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (envelope_id) REFERENCES envelopes (id),
            FOREIGN KEY (card_id) REFERENCES user_cards (id)
        )
    ''')

    # 9. User profile photos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile_photos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 10. User sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_info TEXT,
            ip_address TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            logout_time TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 11. User settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'ukrainian',
            notifications_enabled INTEGER DEFAULT 1,
            biometric_auth INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 12. User levels table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_levels(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            achievements TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 13. User security logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            description TEXT,
            ip_address TEXT,
            device_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 14. AI chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

def fix_database_schema(conn, cursor):
    """Перевіряє та виправляє застарілу схему (наприклад, додає відсутні стовпці)."""
    try:
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'card_id' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN card_id INTEGER")
        
        conn.commit()
    except Exception as e:
        print(f"Schema fix error: {e}")

# --- ХАРДКОД ТА ІНІЦІАЛІЗАЦІЯ ---

def create_initial_test_user(cursor, conn):
    """Створює тестового користувача, якщо у БД відсутні користувачі."""
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            return # Користувачі вже є.

        TEST_EMAIL = "test@app.com"
        TEST_PASSWORD = "testpass" 
        TEST_HASHED_PASSWORD = hash_password(TEST_PASSWORD)
        
        # 1. Створення користувача
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            ("Test_Android_User", TEST_EMAIL, TEST_HASHED_PASSWORD)
        )
        user_id = cursor.lastrowid
        
        # 2. Створення гаманця
        cursor.execute(
            "INSERT INTO wallets (user_id, balance) VALUES (?, ?)",
            (user_id, 0.0)
        )

        # 3. Створення налаштувань та рівня
        cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
        cursor.execute("INSERT INTO user_levels (user_id) VALUES (?)", (user_id,))
        
        # 4. Створення початкової картки з балансом
        cursor.execute(
            "INSERT INTO user_cards (user_id, name, number, bank, balance, color) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "Test Card", "1111222233334444", "Test Bank", 1000.0, json.dumps([0.2, 0.7, 0.9, 1]))
        )
        
        # 5. Логування початкового балансу
        card_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description, card_id)
            VALUES (?, 'income', ?, 'Початковий баланс тестування', ?)
        ''', (user_id, 1000.0, card_id))
        
        conn.commit()
        print(f"!!! АВТОМАТИЧНО СТВОРЕНО ТЕСТОВОГО КОРИСТУВАЧА !!! Email: {TEST_EMAIL}, Пароль: {TEST_PASSWORD}")
        
    except Exception as e:
        print(f"Помилка створення тестового користувача/даних: {traceback.format_exc()}")


def init_database():
    """Initializes and returns database connection and cursor, з надійним копіюванням для Android."""
    db_path = get_db_path()

    # Перевіряємо, чи існує робоча БД до початку процесу
    db_existed = os.path.exists(db_path)

    # --- КЛЮЧОВИЙ КОПІЮВАЛЬНИЙ МЕХАНІЗМ ДЛЯ ANDROID ---
    if platform == 'android' and not db_existed:
        try:
            asset_db_path = resource_find(DB_NAME)
            
            # ВИПРАВЛЕНО: Перевіряємо тільки, чи знайдено ресурс.
            if asset_db_path: 
                # Копіюємо файл з активів до робочого сховища
                shutil.copyfile(asset_db_path, db_path)
                print(f"База даних {DB_NAME} успішно скопійована до шляху запису: {db_path}")
            else:
                print(f"Попередньо заповнена БД не знайдена в активах. Створимо нову.")
        except Exception as e:
            # ВИПРАВЛЕНО: Використовуємо traceback для виведення помилки
            print(f"Помилка копіювання БД на Android: {traceback.format_exc()}")
            
    # --- END КЛЮЧОВИЙ КОПІЮВАЛЬНИЙ МЕХАНІЗМ ---
    
    # Використовуємо check_same_thread=False для Kivy/Android
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    # 1. Створення/Перевірка Схеми
    create_db_schema(cursor)
    
    # 2. Фікс Схеми (якщо потрібно)
    fix_database_schema(conn, cursor) 
    
    # 3. Гарантоване Тестування (Спрацює лише при першому запуску, якщо БД була порожньою)
    if not db_existed:
        create_initial_test_user(cursor, conn)

    return conn, cursor

# --- СТАРТОВІ ФУНКЦІЇ ---

def setup_db():
    global conn, cursor
    if conn is None:
        try:
            conn, cursor = init_database()
        except Exception as e:
            print(f"КРИТИЧНА ПОМИЛКА: Не вдалося ініціалізувати базу даних: {traceback.format_exc()}")
            # Надійна заглушка для запобігання крашу
            class MockConnection:
                def commit(self): pass
                def close(self): pass 
                def cursor(self): 
                    # Повертає mock-курсор
                    return MockCursor()
            class MockCursor:
                def execute(self, *args): pass
                def fetchall(self): return []
                def fetchone(self): return None
                def fetchmany(self, *args): return []
            cursor = MockCursor()
            conn = MockConnection()

# ІНІЦІАЛІЗУЄМО БАЗУ ДАНИХ ОДРАЗУ
setup_db() 

# --- ФУНКЦІОНАЛ (РОБОТА З ДАНИМИ) ---

def create_user(cursor, conn, username, email, password):
    try:
        if not is_valid_email(email):
            return None, "Невірний формат email"
        
        if not is_valid_password(password):
            return None, "Пароль має містити принаймні 6 символів"
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE email=?", (email,))
        if cursor.fetchone()[0] > 0:
            return None, "Користувач з таким email вже існує"
        
        password_hashed = hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password_hashed)
        )
        
        user_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO wallets (user_id, balance) VALUES (?, ?)",
            (user_id, 0.0)
        )

        cursor.execute(
            "INSERT INTO user_settings (user_id) VALUES (?)",
            (user_id,)
        )
        
        cursor.execute(
            "INSERT INTO user_levels (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
        return user_id, "Користувача успішно створено"
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return None, "Помилка створення користувача"

def get_user_by_email(cursor, email):
    try:
        cursor.execute(
            "SELECT id, username, email, password FROM users WHERE email=?",
            (email,)
        )
        user = cursor.fetchone()
        
        if user:
            user_id, username, email, password = user
            return {
                'id': user_id,
                'username': username,
                'email': email,
                'password': password
            }
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def get_profile_photo(cursor, user_id):
    """Отримати шлях до фото профілю (оновлена для Android)"""
    try:
        cursor.execute(
            "SELECT photo_path FROM user_profile_photos WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            photo_path = result[0]
            
            if platform == 'android':
                try:
                    from android.storage import app_storage_path
                    storage_path = app_storage_path()
                    # Перевіряємо кілька можливих шляхів, які можуть бути відносними до app_storage_path
                    possible_paths = [
                        os.path.join(storage_path, photo_path),
                        os.path.join(storage_path, 'profile_photos', os.path.basename(photo_path))
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            return path
                except:
                    pass
            
            # Перевірка для ПК
            if os.path.exists(photo_path):
                return photo_path
            
        return None
    except Exception as e:
        print(f"Помилка отримання фото профілю: {e}")
        return None

def save_profile_photo(cursor, conn, user_id, photo_path):
    """Зберегти шлях до фото (оновлена для Android)"""
    try:
        if platform == 'android':
            try:
                from android.storage import app_storage_path
                storage_path = app_storage_path()
                profile_dir = os.path.join(storage_path, 'profile_photos')
            except:
                profile_dir = "profile_photos" # Резервний шлях для Android
        else:
            profile_dir = "profile_photos" # Шлях для ПК
        
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"profile_{user_id}_{timestamp}.jpg"
        dest_path = os.path.join(profile_dir, filename)
        
        shutil.copy2(photo_path, dest_path)
        
        if platform == 'android':
            try:
                from android.storage import app_storage_path
                storage_path = app_storage_path()
                # Зберігаємо шлях відносний до storage_path
                relative_path = os.path.relpath(dest_path, storage_path)
            except:
                relative_path = dest_path
        else:
            relative_path = dest_path
        
        # Видаляємо старі записи і додаємо новий
        cursor.execute("DELETE FROM user_profile_photos WHERE user_id=?", (user_id,))
        cursor.execute(
            "INSERT INTO user_profile_photos (user_id, photo_path) VALUES (?, ?)",
            (user_id, relative_path)
        )
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Помилка збереження фото: {e}")
        return False

def log_user_session(cursor, conn, user_id, device_info="", ip_address=""):
    try:
        # Деактивуємо всі попередні сесії цього користувача
        cursor.execute(
            "UPDATE user_sessions SET is_active=0 WHERE user_id=?",
            (user_id,)
        )
        
        cursor.execute(
            "INSERT INTO user_sessions (user_id, device_info, ip_address) VALUES (?, ?, ?)",
            (user_id, device_info, ip_address)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error logging user session: {e}")
        return None

def log_user_logout(cursor, conn, session_id):
    try:
        cursor.execute(
            "UPDATE user_sessions SET logout_time=CURRENT_TIMESTAMP, is_active=0 WHERE id=?",
            (session_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error logging user logout: {e}")
        return False

def calculate_session_duration(login_time, logout_time):
    try:
        if not logout_time:
            return "Active"
        
        login_dt = datetime.strptime(login_time, '%Y-%m-%d %H:%M:%S')
        logout_dt = datetime.strptime(logout_time, '%Y-%m-%d %H:%M:%S')
        duration = logout_dt - login_dt
        
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "Unknown"

def get_login_history(cursor, user_id, limit=10):
    try:
        cursor.execute('''
            SELECT device_info, ip_address, login_time, logout_time 
            FROM user_sessions 
            WHERE user_id=? 
            ORDER BY login_time DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        sessions = cursor.fetchall()
        result = []
        
        for session in sessions:
            device_info, ip_address, login_time, logout_time = session
            result.append({
                'device': device_info or "Unknown Device",
                'ip': ip_address or "Unknown IP",
                'login_time': login_time,
                'logout_time': logout_time,
                'duration': calculate_session_duration(login_time, logout_time)
            })
        
        return result
    except Exception as e:
        print(f"Error getting login history: {e}")
        return []

def get_user_settings(cursor, user_id):
    try:
        cursor.execute(
            "SELECT theme, language, notifications_enabled, biometric_auth FROM user_settings WHERE user_id=?",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            theme, language, notifications, biometric = result
            return {
                'theme': theme,
                'language': language,
                'notifications_enabled': bool(notifications),
                'biometric_auth': bool(biometric)
            }
        else:
            # Створення налаштувань за замовчуванням, якщо відсутні
            cursor.execute(
                "INSERT INTO user_settings (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
            return {
                'theme': 'light',
                'language': 'ukrainian',
                'notifications_enabled': True,
                'biometric_auth': False
            }
    except Exception as e:
        print(f"Error getting user settings: {e}")
        return {
            'theme': 'light',
            'language': 'ukrainian',
            'notifications_enabled': True,
            'biometric_auth': False
        }

def update_user_settings(cursor, conn, user_id, theme=None, language=None, notifications_enabled=None, biometric_auth=None):
    try:
        cursor.execute("SELECT id FROM user_settings WHERE user_id=?", (user_id,))
        existing = cursor.fetchone()
        
        params = []
        update_fields = []
            
        if theme is not None:
            update_fields.append("theme=?")
            params.append(theme)
        if language is not None:
            update_fields.append("language=?")
            params.append(language)
        if notifications_enabled is not None:
            update_fields.append("notifications_enabled=?")
            params.append(1 if notifications_enabled else 0)
        if biometric_auth is not None:
            update_fields.append("biometric_auth=?")
            params.append(1 if biometric_auth else 0)
        
        if existing:
            if update_fields:
                update_fields.append("updated_at=CURRENT_TIMESTAMP")
                query = f"UPDATE user_settings SET {', '.join(update_fields)} WHERE user_id=?"
                params.append(user_id)
                cursor.execute(query, params)
        elif update_fields:
            # Якщо запису не існує, але є що оновлювати, створюємо його з початковими значеннями
            cursor.execute('''
                INSERT INTO user_settings 
                (user_id, theme, language, notifications_enabled, biometric_auth) 
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                theme or 'light',
                language or 'ukrainian',
                1 if notifications_enabled is not False else 0,
                1 if biometric_auth else 0
            ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user settings: {e}")
        return False

def get_user_level(cursor, user_id):
    try:
        cursor.execute(
            "SELECT level, experience, achievements FROM user_levels WHERE user_id=?",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            level, experience, achievements_json = result
            
            achievements = json.loads(achievements_json) if achievements_json else []
            
            # Розрахунок XP для наступного рівня
            next_level_xp = level * 100
            progress_percentage = min((experience / next_level_xp) * 100, 100) if level > 0 else 0
            
            return {
                'level': level,
                'experience': experience,
                'achievements': achievements,
                'next_level_xp': next_level_xp,
                'progress_percentage': progress_percentage
            }
        else:
            # Створення запису, якщо відсутній
            cursor.execute(
                "INSERT INTO user_levels (user_id) VALUES (?)",
                (user_id,)
            )
            conn.commit()
            return {
                'level': 1,
                'experience': 0,
                'achievements': [],
                'next_level_xp': 100,
                'progress_percentage': 0
            }
    except Exception as e:
        print(f"Error getting user level: {e}")
        return {
            'level': 1,
            'experience': 0,
            'achievements': [],
            'next_level_xp': 100,
            'progress_percentage': 0
        }

def update_user_experience(cursor, conn, user_id, xp_gained, achievement=None):
    try:
        cursor.execute("SELECT level, experience, achievements FROM user_levels WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        
        if result:
            level, experience, achievements_json = result
            achievements = json.loads(achievements_json) if achievements_json else []
            
            new_experience = experience + xp_gained
            new_level = level
            
            # Логіка підвищення рівня
            while new_experience >= new_level * 100:
                new_experience -= new_level * 100
                new_level += 1
            
            if achievement and achievement not in achievements:
                achievements.append(achievement)
            
            cursor.execute('''
                UPDATE user_levels 
                SET level=?, experience=?, achievements=?, updated_at=CURRENT_TIMESTAMP 
                WHERE user_id=?
            ''', (new_level, new_experience, json.dumps(achievements), user_id))
            
        else:
            # Створення нового запису
            achievements = [achievement] if achievement else []
            cursor.execute('''
                INSERT INTO user_levels (user_id, level, experience, achievements)
                VALUES (?, 1, ?, ?)
            ''', (user_id, xp_gained, json.dumps(achievements)))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user experience: {e}")
        return False

def log_security_action(cursor, conn, user_id, action_type, description="", ip_address="", device_info=""):
    try:
        cursor.execute('''
            INSERT INTO security_logs (user_id, action_type, description, ip_address, device_info)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action_type, description, ip_address, device_info))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error logging security action: {e}")
        return False

def export_user_data(cursor, user_id):
    try:
        cursor.execute("SELECT username, email, created_at FROM users WHERE id=?", (user_id,))
        user_info = cursor.fetchone()
        
        if not user_info:
            return None
        
        username, email, created_at = user_info
        
        export_data = {
            'export_info': {
                'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_id,
                'username': username
            },
            'profile': {
                'username': username,
                'email': email,
                'registration_date': created_at,
                'profile_photo': get_profile_photo(cursor, user_id)
            },
            'financial_data': {
                'cards': get_user_cards(cursor, user_id),
                'transactions': get_user_transactions(cursor, user_id, limit=1000),
                'envelopes': get_user_envelopes(cursor, user_id),
                'savings_plans': get_user_savings_plans(cursor, user_id)
            },
            'settings': get_user_settings(cursor, user_id),
            'levels': get_user_level(cursor, user_id),
            'sessions': get_login_history(cursor, user_id, limit=50)
        }
        
        return export_data
        
    except Exception as e:
        print(f"Error exporting user data: {e}")
        return None

def get_user_savings_plans(cursor, user_id):
    try:
        cursor.execute(
            "SELECT id, name, target_amount, current_amount, deadline, status FROM savings_plans WHERE user_id=?",
            (user_id,)
        )
        plans = cursor.fetchall()
        
        result = []
        for plan in plans:
            plan_id, name, target, current, deadline, status = plan
            result.append({
                'id': plan_id,
                'name': name,
                'target_amount': target,
                'current_amount': current,
                'progress_percentage': (current / target * 100) if target > 0 else 0,
                'deadline': deadline,
                'status': status
            })
        
        return result
    except Exception as e:
        print(f"Error getting savings plans: {e}")
        return []

def get_analytics_data(cursor, user_id, period='month', category=None, card_id=None):
    try:
        end_date = datetime.now()
        
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            SELECT type, amount
            FROM transactions 
            WHERE user_id=? AND created_at BETWEEN ? AND ?
        ''', (user_id, start_date_str, end_date_str))
        
        transactions = cursor.fetchall()

        total_income = 0
        total_expenses = 0
        transactions_count = len(transactions)

        for trans in transactions:
            trans_type, amount = trans
            
            if trans_type in ['deposit', 'card_deposit', 'transfer_in', 'income', 'savings_return', 'savings_completed']:
                total_income += amount
            elif trans_type in ['withdrawal', 'transfer', 'transfer_out', 'expense', 'savings_deposit', 'envelope_deposit']:
                total_expenses += amount

        net_balance = total_income - total_expenses
        
        days_in_period = (end_date - start_date).days or 1
        average_daily = total_expenses / days_in_period

        total_balance = get_total_balance(cursor, user_id)

        savings_rate = (net_balance / total_income * 100) if total_income > 0 else 0

        return {
            'total_income': round(total_income, 2),
            'total_expenses': round(total_expenses, 2),
            'net_balance': round(net_balance, 2),
            'average_daily': round(average_daily, 2),
            'transactions_count': transactions_count,
            'total_balance': round(total_balance, 2),
            'savings_rate': round(savings_rate, 1),
            'period_days': days_in_period
        }
        
    except Exception as e:
        print(f"Error getting analytics data: {e}")
        return {
            'total_income': 0,
            'total_expenses': 0,
            'net_balance': 0,
            'average_daily': 0,
            'transactions_count': 0,
            'total_balance': 0,
            'savings_rate': 0,
            'period_days': 1
        }

def get_category_breakdown(cursor, user_id, period='month'):
    try:
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            SELECT amount, description
            FROM transactions 
            WHERE user_id=? AND type IN ('withdrawal', 'transfer_out', 'expense') 
            AND created_at BETWEEN ? AND ?
        ''', (user_id, start_date_str, end_date_str))
        
        transactions = cursor.fetchall()

        # Стандартні категорії
        categories = {
            'Food': {'amount': 0, 'color': [0.95, 0.3, 0.5, 1]},
            'Transport': {'amount': 0, 'color': [0.2, 0.7, 0.9, 1]},
            'Entertainment': {'amount': 0, 'color': [0.2, 0.8, 0.3, 1]},
            'Bills': {'amount': 0, 'color': [1, 0.6, 0.2, 1]},
            'Shopping': {'amount': 0, 'color': [0.7, 0.4, 0.9, 1]},
            'Other': {'amount': 0, 'color': [0.7, 0.7, 0.7, 1]}
        }

        keywords = {
            'Food': ['food', 'restaurant', 'grocery', 'cafe', 'meal', 'supermarket'],
            'Transport': ['transport', 'bus', 'taxi', 'fuel', 'gas', 'metro', 'train'],
            'Entertainment': ['movie', 'cinema', 'concert', 'game', 'entertainment', 'netflix'],
            'Bills': ['bill', 'rent', 'electricity', 'water', 'internet', 'phone'],
            'Shopping': ['shop', 'store', 'mall', 'clothes', 'electronics', 'purchase']
        }

        for amount, description in transactions:
            description_lower = (description or '').lower()
            categorized = False
            
            for category, words in keywords.items():
                if any(word in description_lower for word in words):
                    categories[category]['amount'] += amount
                    categorized = True
                    break
            
            if not categorized:
                categories['Other']['amount'] += amount

        total_expenses = sum(cat['amount'] for cat in categories.values())
        
        result = []
        for category, data in categories.items():
            if data['amount'] > 0:
                percentage = (data['amount'] / total_expenses * 100) if total_expenses > 0 else 0
                result.append({
                    'name': category,
                    'value': round(percentage, 1),
                    'amount': round(data['amount'], 2),
                    'color': data['color']
                })

        result.sort(key=lambda x: x['amount'], reverse=True)
        
        return result
        
    except Exception as e:
        print(f"Error getting category breakdown: {e}")
        return []

def get_top_categories(cursor, user_id, period='month', limit=5):
    try:
        category_data = get_category_breakdown(cursor, user_id, period)
        return category_data[:limit]
    except Exception as e:
        print(f"Error getting top categories: {e}")
        return []

def get_cards_analytics(cursor, user_id, period='month'):
    try:
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        user_cards = get_user_cards(cursor, user_id)
        cards_analytics = []

        for card in user_cards:
            card_id = card['id']
            
            cursor.execute('''
                SELECT SUM(amount) 
                FROM transactions 
                WHERE user_id=? AND card_id=? AND type IN ('deposit', 'transfer_in', 'income')
                AND created_at BETWEEN ? AND ?
            ''', (user_id, card_id, start_date_str, end_date_str))
            income_result = cursor.fetchone()
            income = income_result[0] or 0

            cursor.execute('''
                SELECT SUM(amount) 
                FROM transactions 
                WHERE user_id=? AND card_id=? AND type IN ('withdrawal', 'transfer_out', 'expense')
                AND created_at BETWEEN ? AND ?
            ''', (user_id, card_id, start_date_str, end_date_str))
            expenses_result = cursor.fetchone()
            expenses = expenses_result[0] or 0

            cards_analytics.append({
                'id': card_id,
                'name': card['name'],
                'income': round(income, 2),
                'expenses': round(expenses, 2),
                'balance': card['balance'],
                'color': card['color']
            })

        return cards_analytics
        
    except Exception as e:
        print(f"Error getting cards analytics: {e}")
        return []

def get_budget_progress(cursor, user_id):
    try:
        envelopes = get_user_envelopes(cursor, user_id)
        budget_data = []
        
        for envelope in envelopes:
            spent = envelope['current_amount']
            limit = envelope['budget_limit']
            percentage = (spent / limit * 100) if limit > 0 else 0
            
            budget_data.append({
                'name': envelope['name'],
                'spent': round(spent, 2),
                'limit': round(limit, 2),
                'percentage': round(percentage, 1),
                'remaining': round(limit - spent, 2),
                'color': envelope['color'],
                'is_overbudget': percentage > 100
            })
        
        return budget_data
        
    except Exception as e:
        print(f"Error getting budget progress: {e}")
        return []

def get_insights_and_forecasts(cursor, user_id):
    try:
        insights = []
        
        # Отримуємо дані за поточний і минулий місяць
        current_data = get_analytics_data(cursor, user_id, 'month')
        
        # Для порівняння з минулим місяцем, робимо запит, зрушуючи період на 30 днів назад
        end_date_prev = datetime.now() - timedelta(days=30)
        start_date_prev = end_date_prev - timedelta(days=30)
        
        prev_data = get_analytics_data(cursor, user_id, period='month') # Використовуємо стандартний місяць
        
        budgets = get_budget_progress(cursor, user_id)
        for budget in budgets:
            if budget['percentage'] > 90:
                insights.append(f" Можлива перевитрата в конверті '{budget['name']}' - використано {budget['percentage']}%")
            elif budget['percentage'] > 75:
                insights.append(f" Конверт '{budget['name']}' майже заповнений - {budget['percentage']}%")
        
        if prev_data['total_expenses'] > 0 and current_data['total_expenses'] > prev_data['total_expenses'] * 1.2:
            increase_percent = ((current_data['total_expenses'] - prev_data['total_expenses']) / prev_data['total_expenses'] * 100)
            insights.append(f" Зростання витрат на {increase_percent:.1f}% порівняно з минулим місяцем")
        
        daily_avg = current_data['average_daily']
        days_in_month = 30
        projected_expenses = daily_avg * days_in_month
        
        insights.append(f" Прогноз витрат до кінця місяця: ${projected_expenses:.2f}")
        
        savings_rate = (current_data['total_income'] - current_data['total_expenses']) / current_data['total_income'] * 100 if current_data['total_income'] > 0 else 0

        if savings_rate > 20:
            insights.append(f" Відмінно! Ваш рівень заощаджень: {savings_rate:.1f}%")
        elif savings_rate < 10:
            insights.append(f" Можна покращити заощадження. Поточний рівень: {savings_rate:.1f}%")
        
        return insights
        
    except Exception as e:
        print(f"Error getting insights: {e}")
        return [" Аналіз даних тимчасово недоступний"]

def get_monthly_comparison(cursor, user_id, months=6):
    try:
        monthly_data = []
        
        for i in range(months):
            month_date = datetime.now() - timedelta(days=30*i)
            month_str = month_date.strftime('%Y-%m')
            
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN type IN ('deposit', 'transfer_in', 'income') THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN type IN ('withdrawal', 'transfer_out', 'expense') THEN amount ELSE 0 END) as expenses
                FROM transactions 
                WHERE user_id=? AND strftime('%Y-%m', created_at) = ?
            ''', (user_id, month_str))
            
            result = cursor.fetchone()
            income = result[0] or 0
            expenses = result[1] or 0
            
            monthly_data.append({
                'month': month_date.strftime('%b %Y'),
                'income': round(income, 2),
                'expenses': round(expenses, 2),
                'savings': round(income - expenses, 2)
            })
        
        monthly_data.reverse()
        return monthly_data
        
    except Exception as e:
        print(f"Error getting monthly comparison: {e}")
        return []

def create_user_card(cursor, conn, user_id, name, number, bank, balance=0.0, color=None):
    try:
        if color is None:
            color = '[0.2, 0.4, 0.8, 1]'
        elif isinstance(color, list):
            color = json.dumps(color)
            
        cursor.execute(
            "INSERT INTO user_cards (user_id, name, number, bank, balance, color) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, number, bank, balance, color)
        )
        conn.commit()
        
        card_id = cursor.lastrowid
        
        log_transaction(cursor, conn, user_id, 'card_creation', 0, f"Створено картку {name}", card_id)
        
        return card_id
    except Exception as e:
        print(f"Error creating user card: {e}")
        return None

def get_user_cards(cursor, user_id):
    try:
        cursor.execute(
            "SELECT id, name, number, bank, balance, color FROM user_cards WHERE user_id=?",
            (user_id,)
        )
        cards = cursor.fetchall()
        
        result = []
        for card in cards:
            card_id, name, number, bank, balance, color = card
            
            result.append({
                'id': card_id,
                'name': name,
                'number': number,
                'bank': bank,
                'balance': balance,
                'color': safe_color_conversion(color)
            })
        
        return result
    except Exception as e:
        print(f"Error getting user cards: {e}")
        return []

def get_user_card_by_id(cursor, card_id):
    try:
        cursor.execute(
            "SELECT id, name, number, bank, balance, color FROM user_cards WHERE id=?",
            (card_id,)
        )
        card = cursor.fetchone()
        
        if card:
            card_id, name, number, bank, balance, color = card
            
            masked_number = f"**** **** **** {number[-4:]}" if number and len(number) >= 4 else "****"
            
            return {
                'id': card_id,
                'name': name,
                'number': masked_number,
                'full_number': number,
                'bank': bank,
                'balance': balance,
                'color': safe_color_conversion(color)
            }
        return None
    except Exception as e:
        print(f"Error getting user card by id: {e}")
        return None

def get_total_balance(cursor, user_id):
    try:
        cursor.execute(
            "SELECT SUM(balance) FROM user_cards WHERE user_id=?",
            (user_id,)
        )
        result = cursor.fetchone()
        total = result[0] if result and result[0] is not None else 0.0
        return total
    except Exception as e:
        print(f"Error getting total balance: {e}")
        return 0.0

def update_card_balance(cursor, conn, card_id, amount, description=""):
    try:
        cursor.execute("SELECT user_id, name, balance FROM user_cards WHERE id=?", (card_id,))
        card_info = cursor.fetchone()
        
        if not card_info:
            return False
            
        user_id, card_name, current_balance = card_info
        new_balance = current_balance + amount
        
        cursor.execute(
            "UPDATE user_cards SET balance=? WHERE id=?",
            (new_balance, card_id)
        )
        conn.commit()
        
        if not description.startswith("(") or "конверт" not in description.lower():
            trans_type = 'deposit' if amount > 0 else 'withdrawal'
            trans_description = f"Поповнення картки {card_name}" if amount > 0 else f"Зняття з картки {card_name}"
            if description:
                trans_description = description
                
            log_transaction(cursor, conn, user_id, trans_type, amount, trans_description, card_id)
        
        return True
    except Exception as e:
        print(f"Error updating card balance: {e}")
        return False

def delete_user_card(cursor, conn, card_id):
    try:
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (card_id,))
        card_info = cursor.fetchone()
        
        cursor.execute("DELETE FROM user_cards WHERE id=?", (card_id,))
        conn.commit()
        
        if card_info:
            user_id, card_name = card_info
            log_transaction(cursor, conn, user_id, 'card_deletion', 0, f"Видалено картку {card_name}", card_id)
        
        return True
    except Exception as e:
        print(f"Error deleting user card: {e}")
        return False

def update_user_card(cursor, conn, card_id, name=None, number=None, bank=None, balance=None, color=None):
    try:
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("name=?")
            params.append(name)
        if number is not None:
            update_fields.append("number=?")
            params.append(number)
        if bank is not None:
            update_fields.append("bank=?")
            params.append(bank)
        if balance is not None:
            update_fields.append("balance=?")
            params.append(balance)
        if color is not None:
            update_fields.append("color=?")
            if isinstance(color, list):
                color = json.dumps(color)
            params.append(color)
            
        if not update_fields:
            return False
            
        update_query = f"UPDATE user_cards SET {', '.join(update_fields)} WHERE id=?"
        params.append(card_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user card: {e}")
        return False

def transfer_money_between_cards(cursor, conn, from_card_id, to_card_id, amount):
    try:
        cursor.execute("SELECT balance, user_id, name FROM user_cards WHERE id=?", (from_card_id,))
        from_result = cursor.fetchone()
        if not from_result:
            return False, "Картку відправника не знайдено"
        
        from_balance, from_user_id, from_card_name = from_result
        
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (to_card_id,))
        to_result = cursor.fetchone()
        if not to_result:
            return False, "Картку отримувача не знайдено"
        
        to_user_id, to_card_name = to_result
        
        if from_balance < amount:
            return False, "Недостатньо коштів на картці"
        
        new_from_balance = from_balance - amount
        cursor.execute("UPDATE user_cards SET balance=? WHERE id=?", (new_from_balance, from_card_id))
        
        new_to_balance_result = cursor.execute("SELECT balance FROM user_cards WHERE id=?", (to_card_id,)).fetchone()
        new_to_balance = (new_to_balance_result[0] if new_to_balance_result else 0) + amount
        cursor.execute("UPDATE user_cards SET balance=? WHERE id=?", (new_to_balance, to_card_id))
        
        conn.commit()
        
        # Логуємо транзакції для обох карток
        log_transaction(cursor, conn, from_user_id, 'transfer_out', -amount, f"Переказ на картку {to_card_name}", from_card_id)
        log_transaction(cursor, conn, to_user_id, 'transfer_in', amount, f"Переказ з картки {from_card_name}", to_card_id)
        
        return True, "Переказ успішний"
    except Exception as e:
        print(f"Error transferring money: {e}")
        return False, "Помилка переказу"

def log_transaction(cursor, conn, user_id, transaction_type, amount, description="", card_id=None):
    try:
        if transaction_type == 'card_creation':
            return True
            
        # Запобігання дублюванню транзакцій протягом 1 хвилини
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE user_id=? AND type=? AND amount=? AND description=? 
            AND created_at > datetime('now', '-1 minute')
        ''', (user_id, transaction_type, amount, description))
        
        recent_count = cursor.fetchone()[0]
        
        if recent_count > 0:
            return True
            
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description, card_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (user_id, transaction_type, amount, description, card_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error logging transaction: {e}")
        return False

def update_envelope(cursor, conn, envelope_id, name=None, budget_limit=None):
    try:
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("name=?")
            params.append(name)
        if budget_limit is not None:
            update_fields.append("budget_limit=?")
            params.append(budget_limit)
            
        if not update_fields:
            return False
            
        update_query = f"UPDATE envelopes SET {', '.join(update_fields)} WHERE id=?"
        params.append(envelope_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating envelope: {e}")
        return False

def get_user_transactions(cursor, user_id, limit=50):
    try:
        cursor.execute('''
            SELECT t.type, t.amount, t.description, t.created_at, c.name as card_name
            FROM transactions t
            LEFT JOIN user_cards c ON t.card_id = c.id
            WHERE t.user_id=?
            ORDER BY t.created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        transactions = cursor.fetchall()
        result = []
        
        for trans in transactions:
            trans_type, amount, description, created_at, card_name = trans
            result.append({
                'type': trans_type,
                'amount': amount,
                'description': description,
                'date': created_at,
                'card_name': card_name
            })
        
        return result
    except Exception as e:
        print(f"Error getting user transactions: {e}")
        return []

def log_savings_transaction(cursor, conn, user_id, plan_id, amount, trans_type, description=""):
    try:
        cursor.execute(
            "INSERT INTO savings_transactions(user_id, plan_id, amount, type, description) VALUES(?, ?, ?, ?, ?)",
            (user_id, plan_id, amount, trans_type, description)
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging savings transaction: {e}")

def create_envelope(cursor, conn, user_id, name, color=None, budget_limit=0.0):
    try:
        if color is None:
            color = '[0.2, 0.4, 0.8, 1]'
        elif isinstance(color, list):
            color = json.dumps(color)
            
        cursor.execute(
            "INSERT INTO envelopes (user_id, name, color, budget_limit) VALUES (?, ?, ?, ?)",
            (user_id, name, color, budget_limit)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error creating envelope: {e}")
        return None

def get_user_envelopes(cursor, user_id):
    try:
        cursor.execute(
            "SELECT id, name, color, budget_limit, current_amount FROM envelopes WHERE user_id=?",
            (user_id,)
        )
        envelopes = cursor.fetchall()
        
        result = []
        for envelope in envelopes:
            env_id, name, color, budget_limit, current_amount = envelope
            result.append({
                'id': env_id,
                'name': name,
                'color': safe_color_conversion(color),
                'budget_limit': budget_limit,
                'current_amount': current_amount,
                'usage_percentage': (current_amount / budget_limit * 100) if budget_limit > 0 else 0
            })
        
        return result
    except Exception as e:
        print(f"Error getting user envelopes: {e}")
        return []

def add_to_envelope(cursor, conn, user_id, envelope_id, amount, description="", card_id=None):
    try:
        cursor.execute(
            "UPDATE envelopes SET current_amount = current_amount + ? WHERE id=?",
            (amount, envelope_id)
        )
        
        cursor.execute(
            "INSERT INTO envelope_transactions (user_id, envelope_id, amount, description, card_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, envelope_id, amount, description, card_id)
        )
        
        envelope_name = get_envelope_name(cursor, envelope_id)
        log_transaction(cursor, conn, user_id, 'envelope_deposit', amount, 
                       f"{description} ({envelope_name})", card_id)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding to envelope: {e}")
        return False

def get_envelope_name(cursor, envelope_id):
    try:
        cursor.execute("SELECT name FROM envelopes WHERE id=?", (envelope_id,))
        result = cursor.fetchone()
        return result[0] if result else "Unknown"
    except Exception as e:
        print(f"Error getting envelope name: {e}")
        return "Unknown"

def get_envelope_transactions(cursor, user_id, envelope_id=None, limit=50):
    try:
        query = '''
            SELECT et.amount, et.description, et.created_at, e.name as envelope_name, c.name as card_name
            FROM envelope_transactions et
            LEFT JOIN envelopes e ON et.envelope_id = e.id
            LEFT JOIN user_cards c ON et.card_id = c.id
            WHERE et.user_id=?
        '''
        params = [user_id]
        
        if envelope_id:
            query += " AND et.envelope_id=?"
            params.append(envelope_id)
            
        query += " ORDER BY et.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        
        result = []
        for trans in transactions:
            amount, description, created_at, envelope_name, card_name = trans
            result.append({
                'amount': amount,
                'description': description,
                'date': created_at,
                'envelope_name': envelope_name,
                'card_name': card_name
            })
        
        return result
    except Exception as e:
        print(f"Error getting envelope transactions: {e}")
        return []

def get_envelope_stats(cursor, user_id):
    try:
        cursor.execute('''
            SELECT 
                e.name,
                e.budget_limit,
                e.current_amount,
                COUNT(et.id) as transaction_count,
                SUM(CASE WHEN et.amount > 0 THEN et.amount ELSE 0 END) as total_deposits
            FROM envelopes e
            LEFT JOIN envelope_transactions et ON e.id = et.envelope_id
            WHERE e.user_id=?
            GROUP BY e.id, e.name, e.budget_limit, e.current_amount
        ''', (user_id,))
        
        stats = cursor.fetchall()
        result = []
        
        for stat in stats:
            name, budget_limit, current_amount, transaction_count, total_deposits = stat
            result.append({
                'name': name,
                'budget_limit': budget_limit,
                'current_amount': current_amount,
                'transaction_count': transaction_count,
                'total_deposits': total_deposits or 0,
                'usage_percentage': (current_amount / budget_limit * 100) if budget_limit > 0 else 0
            })
        
        return result
    except Exception as e:
        print(f"Error getting envelope stats: {e}")
        return []

def debug_transactions(cursor, user_id):
    try:
        cursor.execute(
            "SELECT type, amount, description, created_at FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        transactions = cursor.fetchall()
        return transactions
    except Exception as e:
        print(f"Error debugging transactions: {e}")
        return []


__all__ = [
    'conn', 'cursor', 
    'is_valid_email', 'is_valid_password', 'hash_password', 'check_password',
    'log_transaction', 'log_savings_transaction', 'get_user_transactions',
    'create_user_card', 'get_user_cards', 'get_user_card_by_id', 'get_total_balance', 
    'update_card_balance', 'delete_user_card', 'update_user_card', 'transfer_money_between_cards',
    'safe_color_conversion',
    'create_envelope', 'get_user_envelopes', 'add_to_envelope', 'get_envelope_transactions', 'get_envelope_stats',
    'update_envelope',
    'create_user', 'get_user_by_email',
    'get_analytics_data', 'get_category_breakdown', 'get_top_categories', 
    'get_cards_analytics', 'get_budget_progress', 'get_insights_and_forecasts', 'get_monthly_comparison',
    'debug_transactions',
    'save_profile_photo', 'get_profile_photo',
    'log_user_session', 'log_user_logout', 'get_login_history',
    'get_user_settings', 'update_user_settings',
    'get_user_level', 'update_user_experience',
    'log_security_action', 'export_user_data',
    'get_user_savings_plans',
    'setup_db'
]