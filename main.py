import sys
import os
from kivy.utils import platform

# Додаємо шлях до поточної директорії
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Запит дозволів для Android
if platform == 'android':
    try:
        from android.permissions import request_permissions, Permission
        # Запит лише тих дозволів, які вказані в buildozer.spec
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            Permission.INTERNET, 
            Permission.ACCESS_NETWORK_STATE,
            # Додаємо VIBRATE та WAKE_LOCK, якщо вони потрібні
            Permission.VIBRATE,
            Permission.WAKE_LOCK 
        ])
    except ImportError:
        print("Попередження: android.permissions не знайдено.")

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty

# КРИТИЧНО: Ініціалізація БД виконується тут.
# Змінено імпорт з assets.db_manager на utils.db_manager (як стандартна практика)
from utils.db_manager import setup_db, conn 

from screens.start_screen import StartScreen
from screens.registration_screen import RegistrationScreen
from screens.login_screen import LoginScreen
from screens.dashboard import DashboardScreen
from screens.home_tab import HomeTab
from screens.savings_tab import SavingsTab
from screens.analytics_tab import AnalyticsTab
from screens.account_tab import AccountTab

# Переконайтеся, що файл 'kv/screens.kv' існує
Builder.load_file("kv/screens.kv")

class FinanceScreenManager(ScreenManager):
    current_user = StringProperty("")
    current_user_id = NumericProperty(0)
    balance = NumericProperty(0.0)

class FinanceApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Встановлення початкових значень властивостей
        self.current_user = ""
        self.current_user_id = 0
        self.balance = 0.0

    def build(self):
        # 1. БД ініціалізована в utils/db_manager.py
        
        # Налаштування для Android
        if platform == 'android':
            # Це необхідно, щоб віртуальна клавіатура не перекривала поле введення
            Window.softinput_mode = 'below_target'
            Window.keyboard_anim_args = {'d': 0.2, 't': 'linear'}
        
        # Загальне налаштування вікна
        Window.clearcolor = (0.9, 0.95, 1.0, 1) # Дуже світлий блакитний фон
        
        sm = FinanceScreenManager(transition=SlideTransition(duration=0.2))
        
        # Реєстрація головних екранів
        sm.add_widget(StartScreen(name="start_screen"))
        sm.add_widget(RegistrationScreen(name="registration_screen"))
        sm.add_widget(LoginScreen(name="login_screen"))
        
        # Створюємо dashboard (екран з табами)
        dashboard = DashboardScreen(name="dashboard_screen")
        sm.add_widget(dashboard)
        
        return sm

    def on_start(self):
        """Викликається при запуску додатку"""
        if platform == 'android':
            print("Додаток запущено на Android")
            self.setup_android()

    def setup_android(self):
        """Налаштування для Android: перевірка шляхів до сховища"""
        try:
            from android.storage import app_storage_path
            storage_path = app_storage_path()
            print(f"Шлях до сховища Android: {storage_path}")
            
            # Створюємо необхідні папки для профілю (використовується для Scoped Storage)
            profile_dir = os.path.join(storage_path, 'profile_photos')
            if not os.path.exists(profile_dir):
                os.makedirs(profile_dir)
                print(f"Створено папку для фото профілю: {profile_dir}")
                
        except Exception as e:
            # Це може статися, якщо android.storage не знайдено, наприклад, на емуляторах
            print(f"Помилка налаштування Android: {e}")

    def on_stop(self):
        """Викликається при закритті додатку: закриття з'єднання з БД"""
        if conn:
            conn.close()
            print("З'єднання з базою даних закрито")

if __name__ == "__main__":
    FinanceApp().run()