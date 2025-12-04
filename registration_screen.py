import traceback
from datetime import datetime
import os
import sys

from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
# Припускаємо, що ці утиліти доступні в utils/db_manager.py
try:
    from utils.db_manager import conn, cursor, is_valid_email, is_valid_password, hash_password, log_transaction, get_total_balance
except ImportError:
    # Заглушки для імітації відсутності utils
    class MockCursor:
        def execute(self, *args): pass
        def fetchall(self): return []
        def fetchone(self): return None
    cursor = MockCursor()
    class MockConn:
        def commit(self): pass
    conn = MockConn()
    def is_valid_email(email): return '@' in email
    def is_valid_password(password): return len(password) >= 6
    def hash_password(password): return f"hashed_{password}"
    def log_transaction(*args): pass
    def get_total_balance(*args): return 0.0

class RegistrationScreen(Screen):
 
    def register_user(self):
        """Обробляє реєстрацію нового користувача, перевіряє дані та виконує авто-вхід."""
        
        # ВИПРАВЛЕНО: Доступ до тексту PasswordTextInput через його внутрішній ID
        try:
            username = self.ids.username.text.strip()
            email = self.ids.email.text.strip()
            password = self.ids.password_field.ids.password_input.text.strip()
            password_confirm = self.ids.password_confirm_field.ids.password_input.text.strip()
        except AttributeError:
            # Це може статися, якщо .kv файл не завантажено або ID неправильні
            print(f"Помилка доступу до ID полів вводу в {self.__class__.__name__}")
            return
            
        msg_label = self.ids.reg_message

        if not (username and email and password and password_confirm):
            msg_label.text = "Будь ласка, заповніть усі поля"
            return

        if not is_valid_email(email):
            msg_label.text = "Невірний формат електронної адреси"
            return

        if password != password_confirm:
            msg_label.text = "Паролі не співпадають!"
            return

        if not is_valid_password(password):
            msg_label.text = "Пароль має містити щонайменше 6 символів"
            return

        try:
            # Перевірка, чи існує користувач
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                msg_label.text = "Ця електронна адреса вже зареєстрована"
                self.manager.transition.direction = 'left'
                self.manager.current = "login_screen"
                return

            hashed_pw = hash_password(password)
            
            # 1. Створення користувача
            cursor.execute(
                "INSERT INTO users(username, email, password, created_at) VALUES(?, ?, ?, ?)",
                (username, email, hashed_pw, datetime.now().isoformat())
            )
            conn.commit()

            cursor.execute("SELECT id FROM users WHERE email=?", (email,))
            user_id = cursor.fetchone()[0]

            # 2. Створення гаманця
            cursor.execute("INSERT INTO wallets(user_id, balance) VALUES(?, ?)", (user_id, 0.0))
            conn.commit()
            
            # 3. Логування транзакції
            log_transaction(cursor, conn, user_id, "initial", 0.0, "Створено обліковий запис")

            # 4. Автоматичний вхід
            self.auto_login_after_registration(user_id, username)
            
        except Exception as e:
            msg_label.text = f"Помилка: {str(e)}"
            print(f"Registration error: {traceback.format_exc()}")

    def auto_login_after_registration(self, user_id, username):
        """Встановлює стан програми для входу та переходить на Dashboard."""
        app = App.get_running_app()
        
        try:
            # Очищення полів (для безпеки)
            self.ids.username.text = ""
            self.ids.email.text = ""
            self.ids.password_field.ids.password_input.text = ""
            self.ids.password_confirm_field.ids.password_input.text = ""
            
            # Встановлення глобальних властивостей програми
            app.current_user = username
            app.current_user_id = user_id
            
            # Оновлення балансу (хоча він і нульовий, але встановлюємо стан)
            app.balance = get_total_balance(cursor, user_id) 

            print(f"Auto-login after registration: {username}, user_id: {user_id}")
            
            self.manager.transition.direction = 'left'
            self.manager.current = "dashboard_screen"
            
            # ВИПРАВЛЕНО: Виклик примусового оновлення для Dashboard
            # Запускаємо оновлення після невеликої затримки, щоб менеджер екранів встиг переключитися.
            Clock.schedule_once(lambda dt: self.force_dashboard_update(), 0.1)
            
        except Exception as e:
            print(f"Error during auto-login: {traceback.format_exc()}")
            self.ids.reg_message.text = "Реєстрація успішна! Будь ласка, увійдіть вручну."
            self.manager.transition.direction = 'left'
            self.manager.current = "login_screen"

    def force_dashboard_update(self):
        """Примусово оновлює Dashboard, викликаючи метод оновлення у ньому."""
        dashboard = self.manager.get_screen('dashboard_screen')
        
        # Перевіряємо, чи існує метод оновлення на DashboardScreen
        if hasattr(dashboard, 'update_all_tabs'):
            dashboard.update_all_tabs()
        elif 'home_tab' in dashboard.ids and hasattr(dashboard.ids.tab_manager.get_screen('home_tab'), 'update_content'):
             # Якщо update_all_tabs немає, оновлюємо хоча б HomeTab
            dashboard.ids.tab_manager.get_screen('home_tab').update_content()

