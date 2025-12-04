# screens/dashboard.py

from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock

class DashboardScreen(Screen):

    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.initialize_content, 0.5)
    
    def initialize_content(self, dt):
        print("Dashboard initializing...")
        self.update_all_tabs()
    
    def on_enter(self):
        print("Dashboard screen entered")
        Clock.schedule_once(lambda dt: self.update_all_tabs(), 0.1)
    
    def update_all_tabs(self):
        if hasattr(self.ids, 'tab_manager'):
            print("Updating all tabs...")
     
            # ВИПРАВЛЕНО: Використовуємо 'home_tab'
            home_tab = self.ids.tab_manager.get_screen('home_tab') 
            if home_tab and hasattr(home_tab, 'update_content'):
                print("Found home tab, updating content...")
                home_tab.update_content()
            else:
                print("Home tab not found or no update_content method")
    
    def switch_tab(self, tab_name):
        if hasattr(self.ids, 'tab_manager'):
            # ВИПРАВЛЕНО: Використовуємо повні назви табів для коректної роботи
            available_tabs = ['home_tab', 'analytics_tab', 'savings_tab', 'account_tab']
            
            if tab_name in available_tabs:
                self.ids.tab_manager.current = tab_name

                current_tab = self.ids.tab_manager.current_screen
                if current_tab and hasattr(current_tab, 'update_content'):
                    current_tab.update_content()
    
    def logout(self):
        self.manager.transition.direction = 'right'
        self.manager.current = "start_screen"