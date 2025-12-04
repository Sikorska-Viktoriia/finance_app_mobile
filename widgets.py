# utils/widgets.py

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup  # <--- КРИТИЧНО! Імпортуємо Popup!
from kivy.uix.spinner import Spinner
from kivy.uix.carousel import Carousel
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line
from kivy.properties import (
    StringProperty, 
    BooleanProperty, 
    NumericProperty, 
    ObjectProperty, 
    ListProperty
)
from kivy.app import App
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp

# Кольори
PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1)
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
DARK_GRAY = (0.4, 0.4, 0.4, 1)

class WhitePopup(Popup): # <--- УСПАДКУВАННЯ ВІД Kivy Popup
    
    def __init__(self, **kwargs):
        
        # ВИДАЛЯЄМО З KWARGS ТІ АРГУМЕНТИ, ЯКІ НЕ ПОВИННІ ЙТИ ДО БАЗОВОГО WIDGET
        kwargs.pop('background', None)
        kwargs.pop('background_color', None)
        kwargs.pop('background_normal', None)
        kwargs.pop('background_down', None)
        
        # Popup приймає title та content, тому їх можна передавати
        super().__init__(**kwargs)
        
        # Перепризначаємо, щоб застосувати кастомний фон
        self.background = '' 
        self.background_color = [1, 1, 1, 0] # Прозорий фон для малювання кастомного
        self.separator_height = 0
        # NOTE: Popup.auto_dismiss має бути True за замовчуванням або False.
        # Залишаємо його за замовчуванням, якщо не перевизначено у виклику.
        
        with self.canvas.before:
            Color(*WHITE)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            
            Color(*DARK_GRAY)
            self.border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)),
                width=1.2
            )
        
        self.bind(pos=self._update_graphics, size=self._update_graphics)
    
    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(10))

class WhiteButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = kwargs.get('background_color', PRIMARY_BLUE) 
        self.color = WHITE
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(45)
        self.bold = True
        
        with self.canvas.before:
            Color(*self.background_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(background_color=self._update_color)
    
    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def _update_color(self, instance, value):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*value)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])

class WhiteTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.padding = [dp(15), dp(12)]
        self.background_normal = ''
        self.background_active = ''
        self.background_color = WHITE
        self.foreground_color = DARK_TEXT
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(48)
        self.cursor_color = PRIMARY_BLUE
        self.hint_text_color = DARK_GRAY
        self.write_tab = False
        
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(5)),
                width=1
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(5))

class PasswordTextInput(BoxLayout):
    text = StringProperty("")
    hint_text = StringProperty("")
    password = BooleanProperty(True)
    
    def toggle_password(self):
        self.password = not self.password

class SavingsPlanItem(BoxLayout):
    plan_name = StringProperty("")
    current_amount = NumericProperty(0)
    target_amount = NumericProperty(0)
    progress = NumericProperty(0)
    days_left = NumericProperty(0)
    status = StringProperty("active")
    plan_id = NumericProperty(0)
    background_color = ListProperty([1, 1, 1, 1])
    is_selected = BooleanProperty(False)
    
    on_plan_select = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.on_plan_select:
                self.on_plan_select(self.plan_id, self.plan_name)
            return True
        return super().on_touch_down(touch)

    def get_app(self, *args):
        return App.get_running_app()

class BottomMenuItem(BoxLayout):
    tab_name = StringProperty("")
    icon_source = StringProperty("")
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            dashboard = app.root.get_screen('dashboard_screen') 
            if hasattr(dashboard, 'switch_tab'):
                dashboard.switch_tab(self.tab_name)
            return True 
        return super().on_touch_down(touch)