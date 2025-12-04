from datetime import datetime
import traceback
import os
import base64
import json 
import sys
from kivy.uix.scrollview import ScrollView 

from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.carousel import Carousel
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty
from kivy.graphics import Line, Rectangle, Color, RoundedRectangle
from kivy.utils import platform

# --- ІМПОРТ ТА ЗАГЛУШКИ (для незалежності) ---
# Припускаємо, що ці утиліти доступні в utils/db_manager.py
try:
    from utils.db_manager import cursor, conn, log_transaction, get_user_cards, debug_transactions, get_total_balance, update_card_balance, create_user_card, update_user_card, delete_user_card, transfer_money_between_cards, safe_color_conversion, is_valid_email, is_valid_password, hash_password, check_password
    from utils.widgets import WhitePopup, WhiteButton, WhiteTextInput
except ImportError:
    class MockCursor:
        def execute(self, *args): pass
        def fetchall(self): return []
        def fetchone(self): return None
    cursor = MockCursor()
    class MockConn:
        def commit(self): pass
    conn = MockConn()
    def log_transaction(*args): pass
    def get_user_cards(*args): return [{'id': 1, 'name': 'Demo Card', 'number': '4444', 'bank': 'Mono', 'balance': 100.0, 'color': [0.1, 0.3, 0.6, 1]}]
    def debug_transactions(*args): return []
    def get_total_balance(*args): return 0.0
    def update_card_balance(*args): return True
    def create_user_card(*args): return 1
    def update_user_card(*args): return True
    def delete_user_card(*args): return True
    def transfer_money_between_cards(*args): return True, "Успіх"
    def safe_color_conversion(color): return [0.2, 0.4, 0.8, 1]
    def is_valid_email(email): return '@' in email
    def is_valid_password(password): return len(password) >= 6
    def hash_password(password): return f"hashed_{password}"
    def check_password(input_password, hashed_password): return f"hashed_{input_password}" == hashed_password

    # Заглушки для віджетів
    class WhitePopup(Popup): 
        def __init__(self, **kwargs):
            kwargs.setdefault('title', 'Popup')
            kwargs.setdefault('size_hint', (0.8, 0.8))
            super().__init__(**kwargs)
    class WhiteButton(Button): pass
    
    # Заглушка, що імітує TextInput з коректною ініціалізацією
    class WhiteTextInput(TextInput): 
        def __init__(self, **kwargs):
            # Видаляємо max_text_length, якщо він є, для уникнення помилки ініціалізації
            max_len = kwargs.pop('max_text_length', None) 
            super().__init__(**kwargs)
            if max_len is not None:
                self.max_text_length = max_len


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


# --- MODERN BANK CARD (АДАПТОВАНО) ---

class ModernBankCard(BoxLayout):
    def __init__(self, card_data, **kwargs):
        super().__init__(**kwargs)
        self.card_data = card_data
        self.orientation = 'vertical'
        self.padding = dp(12) # ЗМЕНШЕНО padding
        self.spacing = dp(4) # ЗМЕНШЕНО spacing
        
        color_tuple = self.card_data.get('color') if isinstance(self.card_data.get('color'), list) else safe_color_conversion(self.card_data.get('color'))
        
        self._card_radius = [dp(12)] # ЗМЕНШЕНО радіус
        
        with self.canvas.before:
            Color(*self.get_darker_color(color_tuple))
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self._card_radius)
            
            Color(1, 1, 1, 0.1)
            self.overlay_rect = RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.6),
                size=(self.width, self.height * 0.4),
                radius=self._card_radius
            )
            
            Color(1, 1, 1, 0.4)
            self.border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), # ЗМЕНШЕНО радіус
                width=dp(1)
            )
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
        # --- Вміст картки ---
        header_layout = BoxLayout(size_hint_y=0.2, spacing=dp(8))
        # ЗМЕНШЕНО font_size до dp(10)
        bank_label = Label(text=card_data['bank'], size_hint_x=0.8, font_size=dp(10), bold=True, color=WHITE, halign='left', valign='top') 
        bank_label.bind(size=bank_label.setter('text_size'))
        header_layout.add_widget(bank_label)
        header_layout.add_widget(Label(size_hint_x=0.2))
        self.add_widget(header_layout)
        
        # ЗМЕНШЕНО font_size до dp(14)
        number_label = Label(text=card_data.get('masked_number', '**** **** **** ****'), 
                             font_size=dp(14), color=WHITE, size_hint_y=0.2, valign='middle') 
        self.add_widget(number_label)
        
        # ВИПРАВЛЕНО: Додано Label для імені картки з коректними параметрами
        # ЗМЕНШЕНО font_size до dp(10)
        name_label = Label(text=card_data['name'].upper(), font_size=dp(10), color=(1, 1, 1, 0.9), 
                           halign='left', size_hint_y=0.15, valign='bottom') # ЗБІЛЬШЕНО size_hint_y для кращої видимості
        name_label.bind(size=name_label.setter('text_size'))
        self.add_widget(name_label)
        
        balance_layout = BoxLayout(size_hint_y=0.45) # ЗМЕНШЕНО size_hint_y для корекції
        
        # ЗМЕНШЕНО font_size до dp(18)
        balance_label = Label(text=f"{card_data['balance']:.2f} $", font_size=dp(18), bold=True, 
                              color=WHITE, halign='left', valign='bottom') 
        balance_label.bind(size=balance_label.setter('text_size'))
        
        balance_layout.add_widget(balance_label)
        balance_layout.add_widget(Label())
        self.add_widget(balance_layout)

    def get_darker_color(self, color):
        r, g, b, a = color
        return [max(0, r * 0.7), max(0, g * 0.7), max(0, b * 0.7), a]

    def update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.overlay_rect.pos = (self.x, self.y + self.height * 0.6)
        self.overlay_rect.size = (self.width, self.height * 0.4)
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12)) # ЗМЕНШЕНО радіус
        self.bg_rect.radius = self._card_radius
        self.overlay_rect.radius = self._card_radius


# --- HOME TAB (З ПОВНИМ ФУНКЦІОНАЛОМ І ВИПРАВЛЕНИМИ РОЗМІРАМИ) ---

class HomeTab(Screen):
    
    current_filter = StringProperty("Всі банки")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_scheduled = False
        self.cards_data = []
        self.available_banks = ["Всі банки"]
        self.current_popup = None
        Clock.schedule_once(self.delayed_init, 0.5)
    
    def delayed_init(self, dt):
        self.update_content()
    
    def get_app(self):
        return App.get_running_app()
    
    def on_enter(self):
        if not self._update_scheduled:
            Clock.schedule_once(lambda dt: self.update_content(), 0.1)
            self._update_scheduled = True
    
    def on_pre_enter(self):
        self._update_scheduled = False
    
    def update_content(self):
        app = self.get_app()
        
        if hasattr(app, 'current_user') and app.current_user:
            if 'welcome_label' in self.ids:
                # ЗМЕНШЕНО font_size
                self.ids.welcome_label.font_size = dp(16) 
                self.ids.welcome_label.text = f"Вітаємо, {app.current_user}!"
            
            try:
                cards_balance = get_total_balance(cursor, app.current_user_id)
                
                if 'balance_label' in self.ids:
                    # ЗМЕНШЕНО font_size
                    self.ids.balance_label.font_size = dp(20) 
                    self.ids.balance_label.text = f"Загальний баланс: {cards_balance:.2f} $"
                    
                self.load_user_cards()
                self.update_transactions_history()
                    
            except Exception as e:
                if 'balance_label' in self.ids:
                    self.ids.balance_label.text = "Помилка завантаження"
        else:
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = "Вітаємо!"
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Загальний баланс: 0.00 $"
    
    def load_user_cards(self):
        """Завантажує картки, створюючи маску на основі останніх 4 цифр номера."""
        try:
            app = self.get_app()
            
            raw_cards_data = get_user_cards(cursor, app.current_user_id)
            
            self.cards_data = []
            for card in raw_cards_data:
                processed_card = card.copy()
                
                last_four_digits = card.get('number', '') 
                
                if len(last_four_digits) >= 4 and last_four_digits.isdigit():
                    # ВИПРАВЛЕНО: Коректне форматування маскованого номера
                    processed_card['masked_number'] = f"**** **** **** {last_four_digits}"
                    processed_card['decrypted_number'] = last_four_digits 
                else:
                    processed_card['masked_number'] = "**** **** **** ****"
                    processed_card['decrypted_number'] = None

                self.cards_data.append(processed_card)
            
            self.update_bank_list()
            self.apply_bank_filter()
        
        except Exception as e:
            print(f"Error loading user cards: {traceback.format_exc()}")
            pass
    
    def check_card_exists(self, card_number, current_card_id=None):
        """Перевіряє, чи існує картка з останніми 4 цифрами."""
        try:
            app = self.get_app()
            
            user_cards_data = get_user_cards(cursor, app.current_user_id)
            
            clean_new_number = card_number.replace(" ", "")
            new_last_four = clean_new_number[-4:] if len(clean_new_number) >= 4 else ""
            
            if not new_last_four:
                return True 
            
            for card in user_cards_data:
                existing_last_four = card.get('number', '') 
                
                if existing_last_four == new_last_four:
                    if current_card_id is None or card.get('id') != current_card_id:
                        return True
            
            return False
        except Exception as e:
            print(f"Error checking card existence: {e}")
            return False
    
    def update_bank_list(self):
        banks = set(["Всі банки"])
        
        for card in self.cards_data:
            banks.add(card['bank'])
        
        self.available_banks = sorted(list(banks))
        
        if 'bank_spinner' in self.ids:
            self.ids.bank_spinner.values = self.available_banks
            # ЗМЕНШЕНО font_size
            self.ids.bank_spinner.font_size = dp(14) 
            if self.current_filter in self.available_banks:
                self.ids.bank_spinner.text = self.current_filter
            else:
                self.ids.bank_spinner.text = "Всі банки"
                self.current_filter = "Всі банки"
    
    def apply_bank_filter(self):
        filtered_cards = self.cards_data
        
        if self.current_filter != "Всі банки":
            filtered_cards = [card for card in self.cards_data if card['bank'] == self.current_filter]
        
        self.create_cards_carousel(filtered_cards)
    
    def change_bank_filter(self, bank_name):
        self.current_filter = bank_name
        self.apply_bank_filter()
    
    def create_cards_carousel(self, cards_data=None):
        if 'cards_container' not in self.ids:
            return
            
        if cards_data is None:
            cards_data = self.cards_data
            
        cards_container = self.ids.cards_container
        cards_container.clear_widgets()
        
        carousel = Carousel(
            direction='right',
            loop=False,
            size_hint=(1, 1)
        )
        
        for card_data in cards_data:
            card_widget = self.create_card_with_actions(card_data) 
            carousel.add_widget(card_widget)
        
        if len(cards_data) < 10:
            add_card_button = self.create_add_card_button()
            carousel.add_widget(add_card_button)
        
        cards_container.add_widget(carousel)
    
    def create_card_with_actions(self, card_data):
        main_layout = BoxLayout(
            orientation='vertical',
            size_hint=(0.9, 0.85), # ЗБІЛЬШЕНО size_hint для кращого використання простору
            spacing=dp(8), # ЗМЕНШЕНО spacing
            padding=dp(2) # ЗМЕНШЕНО padding
        )
        
        card = ModernBankCard(card_data, size_hint_y=0.75) 
        main_layout.add_widget(card)
        
        actions_layout = BoxLayout(
            size_hint_y=None,
            height=dp(40), # ЗМЕНШЕНО висоту кнопок
            spacing=dp(8) # ЗМЕНШЕНО spacing
        )
        
        topup_btn = WhiteButton(
            text='Поповнити',
            size_hint_x=0.5,
            background_color=SUCCESS_GREEN,
            color=WHITE,
            bold=True,
            font_size=dp(14) # ЗМЕНШЕНО font_size
        )
        topup_btn.bind(on_press=lambda x: self.show_deposit_modal(card_data))
        
        manage_btn = WhiteButton(
            text='Керувати',
            size_hint_x=0.5,
            background_color=PRIMARY_BLUE,
            color=WHITE,
            bold=True,
            font_size=dp(14) # ЗМЕНШЕНО font_size
        )
        manage_btn.bind(on_press=lambda x: self.show_card_management_modal(card_data))
        
        actions_layout.add_widget(topup_btn)
        actions_layout.add_widget(manage_btn)
        main_layout.add_widget(actions_layout)
        
        return main_layout
    
    def create_add_card_button(self):
        # Логіка створення кнопки додавання картки
        main_layout = BoxLayout(
            orientation='vertical',
            size_hint=(0.9, 0.85), # ЗБІЛЬШЕНО size_hint для кращого використання простору
            padding=dp(2) # ЗМЕНШЕНО padding
        )
        
        add_card_button = Button(
            text="+",
            font_size=dp(40), # ЗМЕНШЕНО font_size
            background_color=(0.3, 0.3, 0.3, 0.2),
            color=(1, 1, 1, 0.8),
            size_hint=(1, 1)
        )
        add_card_button.bind(on_press=self.show_create_card_modal)
        
        with add_card_button.canvas.before:
            add_card_button.bg_rect = RoundedRectangle(radius=[dp(12)]) # ЗМЕНШЕНО радіус
            add_card_button.border_line = Line(width=dp(1)) # ЗМЕНШЕНА ширина
        
        add_card_button.bind(pos=self._update_add_button_graphics, size=self._update_add_button_graphics)
        
        main_layout.add_widget(add_card_button)
        return main_layout
    
    def _update_add_button_graphics(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.4, 0.4, 0.4, 0.3)
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size
            
            Color(0.6, 0.6, 0.6, 0.6)
            instance.border_line.rounded_rectangle = (instance.x, instance.y, 
                                                 instance.width, instance.height, dp(12)) # ЗМЕНШЕНО радіус
            instance.border_line.width = dp(1.5)
            instance.border_line.dash_length = dp(5)
            instance.border_line.dash_offset = dp(5)
    
    # --- Popups (для функціоналу CRUD) ---

    def _create_scrollable_content(self):
        """Створює контейнер ScrollView, готовий для модальних вікон."""
        scrollview = ScrollView(size_hint=(1, 1), do_scroll_y=True)
        # ВИПРАВЛЕНО: ЗМЕНШЕНО PADDING для коректного відображення заголовка
        scroll_layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(10), dp(10), dp(10), dp(10)], size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))
        
        with scroll_layout.canvas.before:
            Color(*WHITE)
            scroll_layout.bg_rect = Rectangle(pos=scroll_layout.pos, size=scroll_layout.size)
            Color(*DARK_GRAY)
            scroll_layout.border_line = Line(rectangle=(scroll_layout.x, scroll_layout.y, scroll_layout.width, scroll_layout.height), width=1.2)
        scroll_layout.bind(pos=lambda inst, val: (setattr(inst.bg_rect, 'pos', val), setattr(inst.border_line, 'rectangle', (inst.x, inst.y, inst.width, inst.height))), 
                           size=lambda inst, val: (setattr(inst.bg_rect, 'size', val), setattr(inst.border_line, 'rectangle', (inst.x, inst.y, inst.width, inst.height))))
        
        scrollview.add_widget(scroll_layout)
        return scrollview, scroll_layout

    def show_create_card_modal(self, instance=None):
        scrollview, content = self._create_scrollable_content()
        
        # ВИПРАВЛЕНО: ЗБІЛЬШЕНО висоту для 2-х рядків та додано логіку переносу
        title = Label(text="Створити нову картку", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(50), halign='center', valign='middle')
        
        def update_title_text_size(label_instance, width):
            label_instance.text_size = (width, None)
            label_instance.texture_update()
            # Додаткова перевірка, якщо висота тексту виходить за межі мінімальної висоти
            if label_instance.texture_size[1] > dp(50):
                 label_instance.height = label_instance.texture_size[1] + dp(10) # Додатковий відступ
            else:
                 label_instance.height = dp(50)

        title.bind(width=update_title_text_size)
        content.add_widget(title)
        
        # ЗМЕНШЕНО height до dp(40)
        name_input = WhiteTextInput(hint_text="Назва картки", size_hint_y=None, height=dp(40))
        content.add_widget(name_input)
        
        # ЗМЕНШЕНО height до dp(40)
        number_input = WhiteTextInput(hint_text="Номер картки (16 цифр)", input_filter='int', size_hint_y=None, height=dp(40), multiline=False)
        number_input.max_text_length = 16 
        content.add_widget(number_input)
        
        # ЗМЕНШЕНО height до dp(40) та font_size
        bank_spinner = Spinner(text="ПриватБанк", values=["ПриватБанк", "Монобанк", "Райффайзен", "Ощадбанк", "Укрексімбанк", "Інший"], size_hint_y=None, height=dp(40), color=DARK_TEXT, background_color=WHITE, halign='left', text_size=(dp(200), dp(40)), font_size=dp(14))
        content.add_widget(bank_spinner)
        
        # ЗМЕНШЕНО font_size та height
        error_label = Label(text="", color=ERROR_RED, font_size=dp(12), size_hint_y=None, height=dp(25))
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8)) # ЗМЕНШЕНО height та spacing
        
        # ЗМЕНШЕНО font_size
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT, font_size=dp(14))
        create_btn = WhiteButton(text="Створити", background_color=PRIMARY_PINK, font_size=dp(14))
        
        def create_card(instance):
            card_name = name_input.text.strip()
            card_number = number_input.text.strip()
            bank_name = bank_spinner.text
            
            if not card_name: error_label.text = "Введіть назву картки"; return
            if len(card_number) != 16: error_label.text = "Введіть коректний номер картки (16 цифр)"; return
            
            if self.check_card_exists(card_number): error_label.text = "Картка з останніми 4 цифрами вже існує"; return
            
            success = self.create_card_from_modal(card_name, card_number, bank_name)
            if success: popup.dismiss()
            else: error_label.text = "Помилка при створенні картки"
        
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        create_btn.bind(on_press=create_card)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(create_btn)
        content.add_widget(buttons_layout)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title=' ', content=scrollview, size_hint=(0.9, 0.65)) 
        self.current_popup = popup
        popup.open()

    def create_card_from_modal(self, card_name, card_number, bank_name):
        try:
            clean_number = card_number.replace(" ", "").strip()
            last_four_digits = clean_number[-4:] 
            
            app = self.get_app()
            
            bank_colors = {
                'ПриватБанк': [0.6, 0.1, 0.1, 1], 'Монобанк': [0.1, 0.3, 0.6, 1],
                'Райффайзен': [0.8, 0.4, 0.0, 1], 'Ощадбанк': [0.0, 0.4, 0.1, 1],
                'Укрексімбанк': [0.4, 0.1, 0.6, 1], 'Інший': [0.2, 0.2, 0.2, 1]
            }
            
            color = bank_colors.get(bank_name, [0.2, 0.4, 0.8, 1])
            
            card_id = create_user_card(
                cursor, conn, app.current_user_id, card_name, 
                last_four_digits, bank_name, 0.0, color
            )
            
            if card_id:
                self.load_user_cards()
                self.show_success_message(f"Картка '{card_name}' успішно створена!")
                return True
            else:
                self.show_error_message("Помилка при створенні картки")
                return False
                
        except Exception as e:
            print(f"Error creating card from modal: {traceback.format_exc()}")
            self.show_error_message("Сталася помилка")
            return False

    def show_card_management_modal(self, card_data):
        scrollview, content = self._create_scrollable_content()
        
        # ВИПРАВЛЕНО: ЗБІЛЬШЕНО висоту для 2-х рядків та додано логіку переносу
        title = Label(text=f"Керування карткою: {card_data['name']}", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(50), valign='middle', halign='center')
        
        def update_title_text_size(label_instance, width):
            label_instance.text_size = (width, None)
            label_instance.texture_update()
            if label_instance.texture_size[1] > dp(50):
                 label_instance.height = label_instance.texture_size[1] + dp(10)
            else:
                 label_instance.height = dp(50)

        title.bind(width=update_title_text_size)
        content.add_widget(title)
        
        # ЗМЕНШЕНО font_size та height
        balance_label = Label(text=f"Баланс: ${card_data['balance']:.2f}", font_size=dp(14), color=DARK_TEXT, size_hint_y=None, height=dp(25))
        content.add_widget(balance_label)
        
        buttons_layout = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None, height=dp(140)) # ЗМЕНШЕНО height та spacing
        
        # ЗМЕНШЕНО height та font_size
        edit_btn = WhiteButton(text="Редагувати картку", background_color=PRIMARY_BLUE, height=dp(40), size_hint_y=None, font_size=dp(14))
        edit_btn.bind(on_press=lambda x: (self.current_popup.dismiss(), self.show_edit_card_modal(card_data)))
        buttons_layout.add_widget(edit_btn)
        
        # ЗМЕНШЕНО height та font_size
        transfer_btn = WhiteButton(text="Переказати гроші", background_color=(0.8, 0.6, 0.2, 1), height=dp(40), size_hint_y=None, font_size=dp(14))
        transfer_btn.bind(on_press=lambda x: (self.current_popup.dismiss(), self.show_transfer_modal(card_data)))
        buttons_layout.add_widget(transfer_btn)
        
        # ЗМЕНШЕНО height та font_size
        delete_btn = WhiteButton(text="Видалити картку", background_color=ERROR_RED, height=dp(40), size_hint_y=None, font_size=dp(14))
        delete_btn.bind(on_press=lambda x: (self.current_popup.dismiss(), self.show_delete_confirmation(card_data)))
        buttons_layout.add_widget(delete_btn)
        
        content.add_widget(buttons_layout)
        
        content.add_widget(Label(size_hint_y=None, height=dp(5)))
        
        # ЗМЕНШЕНО height та font_size
        close_btn = WhiteButton(text="Закрити", background_color=LIGHT_GRAY, color=DARK_TEXT, height=dp(40), size_hint_y=None, font_size=dp(14))
        close_btn.bind(on_press=lambda x: self.current_popup.dismiss())
        content.add_widget(close_btn)
        
        # ЗМЕНШЕНО size_hint
        self.current_popup = WhitePopup(title=' ', content=scrollview, size_hint=(0.85, 0.5)) 
        self.current_popup.open()

    def show_deposit_modal(self, card_data):
        scrollview, content = self._create_scrollable_content()
        
        # ВИПРАВЛЕНО: ЗБІЛЬШЕНО висоту для 2-х рядків та додано логіку переносу
        title = Label(text=f"Поповнення картки: {card_data['name']}", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(50), valign='middle', halign='center')
        
        def update_title_text_size(label_instance, width):
            label_instance.text_size = (width, None)
            label_instance.texture_update()
            if label_instance.texture_size[1] > dp(50):
                 label_instance.height = label_instance.texture_size[1] + dp(10)
            else:
                 label_instance.height = dp(50)

        title.bind(width=update_title_text_size)
        content.add_widget(title)
        
        # ЗМЕНШЕНО height
        amount_input = WhiteTextInput(hint_text="Сума для поповнення", input_filter='float', size_hint_y=None, height=dp(40))
        content.add_widget(amount_input)
        
        # ЗМЕНШЕНО height та font_size
        error_label = Label(text="", color=ERROR_RED, size_hint_y=None, height=dp(25), font_size=dp(12))
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8)) # ЗМЕНШЕНО height та spacing
        
        # ЗМЕНШЕНО font_size
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT, font_size=dp(14))
        deposit_btn = WhiteButton(text="Поповнити", background_color=SUCCESS_GREEN, font_size=dp(14))
        
        def deposit_to_card(instance):
            try:
                amount_text = amount_input.text.strip()
                if not amount_text: error_label.text = "Введіть суму"; return
                    
                amount = float(amount_text)
                if amount <= 0: error_label.text = "Сума має бути додатною"; return
                    
                success = update_card_balance(cursor, conn, card_data['id'], amount)
                
                if success:
                    self.current_popup.dismiss()
                    self.load_user_cards()
                    self.update_content()
                    self.show_success_message(f"Картку '{card_data['name']}' поповнено на {amount:.2f} $!")
                else:
                    error_label.text = "Помилка при поповненні картки"
                    
            except ValueError: error_label.text = "Введіть коректну суму"
            except Exception as e: error_label.text = f"Помилка: {str(e)}"
        
        deposit_btn.bind(on_press=deposit_to_card)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(deposit_btn)
        content.add_widget(buttons_layout)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title=' ', content=scrollview, size_hint=(0.85, 0.4)) 
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        self.current_popup = popup
        popup.open()

    def show_edit_card_modal(self, card_data):
        scrollview, content = self._create_scrollable_content()
        
        # ВИПРАВЛЕНО: ЗБІЛЬШЕНО висоту для 2-х рядків та додано логіку переносу
        title = Label(text="Редагувати картку", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(50), valign='middle', halign='center')
        
        def update_title_text_size(label_instance, width):
            label_instance.text_size = (width, None)
            label_instance.texture_update()
            if label_instance.texture_size[1] > dp(50):
                 label_instance.height = label_instance.texture_size[1] + dp(10)
            else:
                 label_instance.height = dp(50)

        title.bind(width=update_title_text_size)
        content.add_widget(title)
        
        decrypted_number = card_data.get('decrypted_number', '') 
        
        # ЗМЕНШЕНО height
        name_input = WhiteTextInput(text=card_data['name'], hint_text="Назва картки", size_hint_y=None, height=dp(40))
        content.add_widget(name_input)
        
        # ЗМЕНШЕНО height
        number_input = WhiteTextInput(text="", hint_text="Номер картки (16 цифр - не зберігається)", input_filter='int', size_hint_y=None, height=dp(40), multiline=False)
        number_input.max_text_length = 16 
        content.add_widget(number_input)
        
        # ЗМЕНШЕНО height та font_size
        content.add_widget(Label(text=f"Поточний маскований номер: {card_data.get('masked_number', '**** **** **** ****')}", font_size=dp(10), color=DARK_GRAY, size_hint_y=None, height=dp(20)))
        
        # ЗМЕНШЕНО height та font_size
        bank_spinner = Spinner(text=card_data['bank'], values=["ПриватБанк", "Монобанк", "Райффайзен", "Ощадбанк", "Укрексімбанк", "Інший"], size_hint_y=None, height=dp(40), color=DARK_TEXT, background_color=WHITE, halign='left', text_size=(dp(200), dp(40)), font_size=dp(14))
        content.add_widget(bank_spinner)
        
        # ЗМЕНШЕНО height та font_size
        error_label = Label(text="", color=ERROR_RED, size_hint_y=None, height=dp(25), font_size=dp(12))
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8)) # ЗМЕНШЕНО height та spacing
        
        # ЗМЕНШЕНО font_size
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT, font_size=dp(14))
        save_btn = WhiteButton(text="Зберегти", background_color=PRIMARY_PINK, font_size=dp(14))
        
        def save_changes(instance):
            new_name = name_input.text.strip()
            new_number = number_input.text.strip()
            new_bank = bank_spinner.text
            
            if not new_name: error_label.text = "Введіть назву картки"; return
            
            number_to_save = card_data.get('decrypted_number')
            
            if new_number:
                if len(new_number) != 16 or not new_number.isdigit(): error_label.text = "Введіть коректний номер картки (16 цифр)"; return
                
                new_last_four = new_number[-4:] 
                
                if new_last_four != card_data.get('decrypted_number') and self.check_card_exists(new_number, current_card_id=card_data['id']):
                    error_label.text = "Картка з цими 4 цифрами вже існує"; return
                
                number_to_save = new_last_four
                
            bank_colors = {'ПриватБанк': [0.6, 0.1, 0.1, 1], 'Монобанк': [0.1, 0.3, 0.6, 1], 'Райффайзен': [0.8, 0.4, 0.0, 1], 'Ощадбанк': [0.0, 0.4, 0.1, 1], 'Укрексімбанк': [0.4, 0.1, 0.6, 1], 'Інший': [0.2, 0.2, 0.2, 1]}
            color_to_save = bank_colors.get(new_bank, [0.2, 0.4, 0.8, 1])
            
            success = update_user_card(
                cursor, conn, card_data['id'],
                name=new_name, number=number_to_save, bank=new_bank, color=color_to_save
            )
            
            if success:
                self.current_popup.dismiss()
                self.load_user_cards()
                self.update_content()
                self.show_success_message("Картку успішно оновлено!")
            else:
                error_label.text = "Помилка при оновленні картки"
        
        save_btn.bind(on_press=save_changes)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(save_btn)
        content.add_widget(buttons_layout)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title=' ', content=scrollview, size_hint=(0.9, 0.65)) 
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        self.current_popup = popup
        popup.open()

    def show_delete_confirmation(self, card_data):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15)) # ЗМЕНШЕНО spacing та padding
        
        # МАЛЮВАННЯ ФОНУ КОНТЕНТУ (для невеликого popup)
        with content.canvas.before:
            Color(*WHITE); Rectangle(pos=content.pos, size=content.size)
            Color(*DARK_GRAY); Line(rectangle=(content.x, content.y, content.width, content.height), width=1.2)
        
        # ВИПРАВЛЕНО: ЗБІЛЬШЕНО висоту для 2-х рядків та додано логіку переносу
        title = Label(text=f"Видалити картку {card_data['name']}?", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(50), valign='middle', halign='center')
        
        def update_title_text_size(label_instance, width):
            label_instance.text_size = (width, None)
            label_instance.texture_update()
            if label_instance.texture_size[1] > dp(50):
                 label_instance.height = label_instance.texture_size[1] + dp(10)
            else:
                 label_instance.height = dp(50)

        title.bind(width=update_title_text_size)
        content.add_widget(title)
        
        # ЗМЕНШЕНО height та font_size
        warning_label = Label(text="Цю дію не можна скасувати!", color=ERROR_RED, size_hint_y=None, height=dp(25), font_size=dp(12))
        content.add_widget(warning_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8)) # ЗМЕНШЕНО height та spacing
        
        # ЗМЕНШЕНО font_size
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT, font_size=dp(14))
        delete_btn = WhiteButton(text="Видалити", background_color=ERROR_RED, font_size=dp(14))
        
        def delete_card(instance):
            success = delete_user_card(cursor, conn, card_data['id'])
            if success:
                self.current_popup.dismiss()
                self.load_user_cards()
                self.update_content()
                self.show_success_message("Картку успішно видалено!")
            else:
                self.show_error_message("Помилка при видаленні картки")
        
        delete_btn.bind(on_press=delete_card)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(delete_btn)
        content.add_widget(buttons_layout)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title=' ', content=content, size_hint=(0.8, 0.35)) # Збільшено для розміщення 2-х рядків тексту
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        self.current_popup = popup
        popup.open()

    def show_transfer_modal(self, from_card_data):
        scrollview, content = self._create_scrollable_content()
        
        # ВИПРАВЛЕНО: ЗБІЛЬШЕНО висоту для 2-х рядків та додано логіку переносу
        title = Label(text=f"Переказ з картки: {from_card_data['name']}", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(50), valign='middle', halign='center')
        
        def update_title_text_size(label_instance, width):
            label_instance.text_size = (width, None)
            label_instance.texture_update()
            if label_instance.texture_size[1] > dp(50):
                 label_instance.height = label_instance.texture_size[1] + dp(10)
            else:
                 label_instance.height = dp(50)

        title.bind(width=update_title_text_size)
        content.add_widget(title)
        
        other_cards = [card for card in self.cards_data if card['id'] != from_card_data['id']]
        if not other_cards:
            # Обробка випадку відсутності інших карток
            # ЗМЕНШЕНО height та font_size
            error_label = Label(text="Немає інших карток для переказу", color=ERROR_RED, size_hint_y=None, height=dp(30), font_size=dp(12))
            content.clear_widgets() # Очищаємо попередній контент
            content.add_widget(title)
            content.add_widget(error_label)
            # ЗМЕНШЕНО height та font_size
            close_btn = WhiteButton(text="Закрити", background_color=LIGHT_GRAY, color=DARK_TEXT, size_hint_y=None, height=dp(40), font_size=dp(14))
            
            # Створюємо Popup тут, якщо немає інших карток
            # ЗМЕНШЕНО size_hint
            self.current_popup = WhitePopup(title=' ', content=scrollview, size_hint=(0.8, 0.4))
            close_btn.bind(on_press=lambda x: self.current_popup.dismiss())
            content.add_widget(close_btn)
            self.current_popup.open()
            return
        
        # ЗМЕНШЕНО height та font_size
        to_card_spinner = Spinner(text=other_cards[0]['name'], values=[card['name'] for card in other_cards], size_hint_y=None, height=dp(40), color=DARK_TEXT, background_color=WHITE, halign='left', text_size=(dp(200), dp(40)), font_size=dp(14))
        content.add_widget(to_card_spinner)
        
        # ЗМЕНШЕНО height
        amount_input = WhiteTextInput(hint_text="Сума для переказу", input_filter='float', size_hint_y=None, height=dp(40))
        content.add_widget(amount_input)
        
        # ЗМЕНШЕНО height та font_size
        balance_label = Label(text=f"Доступно: ${from_card_data['balance']:.2f}", size_hint_y=None, height=dp(25), color=DARK_TEXT, font_size=dp(12))
        content.add_widget(balance_label)
        
        # ЗМЕНШЕНО height та font_size
        error_label = Label(text="", color=ERROR_RED, size_hint_y=None, height=dp(25), font_size=dp(12))
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(8)) # ЗМЕНШЕНО height та spacing
        
        # ЗМЕНШЕНО font_size
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT, font_size=dp(14))
        transfer_btn = WhiteButton(text="Переказати", background_color=SUCCESS_GREEN, font_size=dp(14))

        def transfer_money(instance):
            try:
                amount_text = amount_input.text.strip()
                if not amount_text: error_label.text = "Введіть суму"; return
                amount = float(amount_text)
                if amount <= 0: error_label.text = "Сума має бути додатною"; return
                if amount > from_card_data['balance']: error_label.text = "Недостатньо коштів"; return
                    
                to_card_name = to_card_spinner.text
                to_card_id = next((card['id'] for card in other_cards if card['name'] == to_card_name), None)
                    
                if not to_card_id: error_label.text = "Картку отримувача не знайдено"; return
                    
                success, message = transfer_money_between_cards(
                    cursor, conn, from_card_data['id'], to_card_id, amount
                )
                
                if success:
                    self.current_popup.dismiss()
                    self.load_user_cards()
                    self.update_content()
                    self.show_success_message(f"Переказ {amount:.2f} $ успішний!")
                else:
                    error_label.text = message
                    
            except ValueError: error_label.text = "Введіть коректну суму"
            except Exception as e: error_label.text = f"Помилка: {str(e)}"
        
        transfer_btn.bind(on_press=transfer_money)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(transfer_btn)
        content.add_widget(buttons_layout)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title=' ', content=scrollview, size_hint=(0.9, 0.6)) 
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        self.current_popup = popup
        popup.open()

  
    def update_transactions_history(self):
        if 'history_container' not in self.ids: return

        history_container = self.ids.history_container
        history_container.clear_widgets()
        history_container.orientation = 'vertical'
        history_container.size_hint_y = None
        history_container.bind(minimum_height=history_container.setter('height'))

        try:
            app = self.get_app()
            
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                # ЗМЕНШЕНО font_size та height
                history_container.add_widget(Label(text="Увійдіть в систему", font_size=dp(14), color=DARK_GRAY, size_hint_y=None, height=dp(30)))
                return
            
            # Обгортаємо виклик БД в окремий try/except для ідентифікації проблем з даними
            try:
                transactions = debug_transactions(cursor, app.current_user_id)
            except Exception as e:
                print(f"Помилка БД при отриманні транзакцій: {traceback.format_exc()}")
                # ЗМЕНШЕНО font_size та height
                history_container.add_widget(Label(text="Помилка БД при завантаженні історії", color=ERROR_RED, size_hint_y=None, height=dp(30)))
                return

            if not transactions:
                # ЗМЕНШЕНО font_size та height
                history_container.add_widget(Label(text="Ще немає транзакцій", font_size=dp(14), color=DARK_GRAY, size_hint_y=None, height=dp(60)))
                return

            # --- Визначення фіксованої ширини для стовпців "Дата" та "Сума" ---
            DATE_WIDTH = dp(60)  # ЗМЕНШЕНО
            AMOUNT_WIDTH = dp(75) # ЗМЕНШЕНО
            # Додатковий простір між стовпцями
            SPACING = dp(4) # ЗМЕНШЕНО
            
            # Заголовок
            # ЗМЕНШЕНО height
            header_layout = BoxLayout(size_hint_y=None, height=dp(25), padding=[SPACING, SPACING, SPACING, SPACING], spacing=SPACING)
            
            # ЗМЕНШЕНО font_size
            header_layout.add_widget(Label(text="Дата", size_hint_x=None, width=DATE_WIDTH, color=DARK_GRAY, font_size=dp(10), bold=True, halign='left'))
            header_layout.add_widget(Label(text="Опис", size_hint_x=1, color=DARK_GRAY, font_size=dp(10), bold=True, halign='left')) 
            header_layout.add_widget(Label(text="Сума", size_hint_x=None, width=AMOUNT_WIDTH, color=DARK_GRAY, font_size=dp(10), bold=True, halign='right'))
            history_container.add_widget(header_layout)

            filtered_transactions = []
            seen_transactions = set()
            
            for trans in transactions:
                # Перевірка формату транзакції (4 елементи)
                if len(trans) != 4:
                    print(f"Пропущено некоректну транзакцію: {trans}")
                    continue
                
                trans_type, amount, description, created_at = trans
                
                if trans_type == 'card_creation': continue
                
                # Припускаємо, що created_at є унікальним
                trans_key = (trans_type, amount, description, created_at) 
                
                if trans_key not in seen_transactions:
                    seen_transactions.add(trans_key)
                    filtered_transactions.append(trans)

            # --- ЗМІНА: Встановлення ліміту для опису ---
            MAX_DESC_LENGTH = 18 # ЗМЕНШЕНО
            
            for i, (trans_type, amount, description, created_at) in enumerate(filtered_transactions):
                try:
                    date_time = datetime.now() 
                    date_str = date_time.strftime('%d.%m %H:%M')

                    if trans_type in ('deposit', 'savings_return', 'card_deposit', 'savings_interest', 'savings_completed', 'transfer_in', 'income', 'envelope_deposit'):
                        amount_color = SUCCESS_GREEN
                        sign = "+"
                    else:
                        amount_color = ERROR_RED
                        sign = "-"
                        
                    # Скорочення опису, якщо він занадто довгий
                    display_description = description
                    if len(description) > MAX_DESC_LENGTH:
                        display_description = description[:MAX_DESC_LENGTH].strip() + "..."

                    # ВИПРАВЛЕНО: Додано spacing=SPACING
                    trans_layout = BoxLayout(size_hint_y=None, padding=[SPACING, SPACING, SPACING, SPACING], spacing=SPACING) 
                    
                    
                    # --- Ініціалізація віджетів для рядка (з фіксованою шириною) ---
                    
                    # ЗМЕНШЕНО font_size
                    date_label = Label(text=date_str, size_hint_x=None, width=DATE_WIDTH, color=DARK_TEXT, font_size=dp(9), valign='top', halign='left')
                    
                    # Опис (size_hint_x=1) - використовуємо скорочений текст, ЗМЕНШЕНО font_size
                    desc_label = Label(text=display_description, size_hint_x=1, color=DARK_TEXT, font_size=dp(11), halign='left', valign='top')
                    
                    # ЗМЕНШЕНО font_size
                    amount_label = Label(text=f"{sign}{abs(amount):.2f} $", size_hint_x=None, width=AMOUNT_WIDTH, color=amount_color, font_size=dp(11), bold=True, valign='top', halign='right')

                    # --- Логіка динамічної висоти ---
                    def set_min_height(instance, width):
                        # width - загальна ширина BoxLayout
                        # Розрахунок ширини, доступної для поля "Опис"
                        # Віднімаємо фіксовані ширини, два SPACING (між колонками) та два SPACING (padding BoxLayout)
                        # NOTE: Оскільки ми скоротили текст, переносу може не бути, але логіку зберігаємо
                        desc_width = width - DATE_WIDTH - AMOUNT_WIDTH - (3 * SPACING)
                        
                        # Встановлюємо text_size для автоматичного переносу (залишаємо на випадок, якщо скорочення недостатнє)
                        desc_label.text_size = (desc_width, None)
                        
                        desc_label.texture_update()
                        min_h_desc = desc_label.texture_size[1]
                        
                        # Додаємо вертикальний padding. ЗМЕНШЕНО min_height
                        min_h_new = max(dp(25), min_h_desc + dp(8)) 
                        
                        instance.height = min_h_new
                        instance.minimum_height = min_h_new
                        date_label.height = min_h_new
                        amount_label.height = min_h_new
                        desc_label.height = min_h_new

                    # Прив'язка динамічного оновлення висоти до зміни ширини контейнера
                    trans_layout.bind(width=set_min_height)
                    
                    with trans_layout.canvas.before:
                        bg_color = (0.98, 0.98, 0.98, 1) if i % 2 == 0 else (0.95, 0.95, 0.95, 1)
                        Color(*bg_color)
                        trans_layout.bg_rect = Rectangle(pos=trans_layout.pos, size=trans_layout.size)
                    
                    trans_layout.bind(pos=lambda inst, val: setattr(inst.bg_rect, 'pos', val), size=lambda inst, val: setattr(inst.bg_rect, 'size', val))
                    
                    trans_layout.add_widget(date_label)
                    trans_layout.add_widget(desc_label)
                    trans_layout.add_widget(amount_label)
                    history_container.add_widget(trans_layout)
                    
                    # Примусове оновлення розміру після додавання віджетів
                    Clock.schedule_once(lambda dt: set_min_height(trans_layout, history_container.width), 0)


                except Exception as e:
                    # Виведення детальної помилки, якщо збій стався при обробці одного рядка
                    print(f"Помилка обробки окремої транзакції {i}: {traceback.format_exc()}")
                    # ЗМЕНШЕНО font_size та height
                    history_container.add_widget(Label(text=f"Помилка в рядку {i}", color=ERROR_RED, size_hint_y=None, height=dp(25)))
                    continue

        except Exception as e:
            # Цей блок ловить критичні помилки, які не були спіймані вище
            print(f"Критична помилка в update_transactions_history: {traceback.format_exc()}")
            # ЗМЕНШЕНО font_size та height
            history_container.add_widget(Label(text="Критична помилка завантаження історії", color=ERROR_RED, size_hint_y=None, height=dp(30)))
    
    def show_success_message(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(15)) # ЗМЕНШЕНО spacing та padding
        
        with content.canvas.before:
            Color(*WHITE); Rectangle(pos=content.pos, size=content.size)
            Color(*DARK_GRAY); Line(rectangle=(content.x, content.y, content.width, content.height), width=1.2)
        
        # ЗМЕНШЕНО font_size
        content.add_widget(Label(text=message, color=SUCCESS_GREEN, font_size=dp(14)))
        
        # ЗМЕНШЕНО height та font_size
        ok_btn = WhiteButton(text='OK', background_color=PRIMARY_PINK, size_hint_y=None, height=dp(35), font_size=dp(14))
        ok_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title='Успіх', content=content, size_hint=(0.7, 0.25))
        popup.open()

    def show_error_message(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(15)) # ЗМЕНШЕНО spacing та padding
        
        with content.canvas.before:
            Color(*WHITE); Rectangle(pos=content.pos, size=content.size)
            Color(*DARK_GRAY); Line(rectangle=(content.x, content.y, content.width, content.height), width=1.2)
        
        # ЗМЕНШЕНО font_size
        content.add_widget(Label(text=message, color=ERROR_RED, font_size=dp(14)))
        
        # ЗМЕНШЕНО height та font_size
        ok_btn = WhiteButton(text='OK', background_color=PRIMARY_BLUE, size_hint_y=None, height=dp(35), font_size=dp(14))
        ok_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        
        # ЗМЕНШЕНО size_hint
        popup = WhitePopup(title='Помилка', content=content, size_hint=(0.7, 0.25))
        popup.open()


# --- REGISTRATION SCREEN LOGIC (без змін розмірів) ---

class RegistrationScreen(Screen):
 
    def register_user(self):
        """Обробляє реєстрацію нового користувача, перевіряє дані та виконує авто-вхід."""
        
        try:
            username = self.ids.username.text.strip()
            email = self.ids.email.text.strip()
            # Доступ до внутрішнього поля PasswordTextInput
            password = self.ids.password_field.ids.password_input.text.strip()
            password_confirm = self.ids.password_confirm_field.ids.password_input.text.strip()
        except AttributeError:
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
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                msg_label.text = "Ця електронна адреса вже зареєстрована"
                self.manager.transition.direction = 'left'
                self.manager.current = "login_screen"
                return

            hashed_pw = hash_password(password)
            
            cursor.execute(
                "INSERT INTO users(username, email, password, created_at) VALUES(?, ?, ?, ?)",
                (username, email, hashed_pw, datetime.now().isoformat())
            )
            conn.commit()

            cursor.execute("SELECT id FROM users WHERE email=?", (email,))
            user_id = cursor.fetchone()[0]

            cursor.execute("INSERT INTO wallets(user_id, balance) VALUES(?, ?)", (user_id, 0.0))
            conn.commit()
            
            log_transaction(cursor, conn, user_id, "initial", 0.0, "Створено обліковий запис")

            self.auto_login_after_registration(user_id, username)
            
        except Exception as e:
            msg_label.text = f"Помилка: {str(e)}"
            print(f"Registration error: {traceback.format_exc()}")

    def auto_login_after_registration(self, user_id, username):
        """Встановлює стан програми для входу та переходить на Dashboard."""
        app = App.get_running_app()
        
        try:
            self.ids.username.text = ""
            self.ids.email.text = ""
            self.ids.password_field.ids.password_input.text = ""
            self.ids.password_confirm_field.ids.password_input.text = ""
            
            app.current_user = username
            app.current_user_id = user_id
            app.balance = get_total_balance(cursor, user_id) 

            self.manager.transition.direction = 'left'
            self.manager.current = "dashboard_screen"
            
            Clock.schedule_once(lambda dt: self.force_dashboard_update(), 0.1)
            
        except Exception as e:
            print(f"Error during auto-login: {traceback.format_exc()}")
            self.ids.reg_message.text = "Реєстрація успішна! Будь ласка, увійдіть вручну."
            self.manager.transition.direction = 'left'
            self.manager.current = "login_screen"

    def force_dashboard_update(self):
        """Примусово оновлює Dashboard, викликаючи метод оновлення у ньому."""
        dashboard = self.manager.get_screen('dashboard_screen')
        
        if hasattr(dashboard, 'update_all_tabs'):
            dashboard.update_all_tabs()
        elif 'home_tab' in dashboard.ids and hasattr(dashboard.ids.tab_manager.get_screen('home_tab'), 'update_content'):
            dashboard.ids.tab_manager.get_screen('home_tab').update_content()

# --- LOGIN SCREEN LOGIC (без змін розмірів) ---

class LoginScreen(Screen):

    def login_user(self):
        """Обробляє вхід користувача, перевіряє пароль і встановлює стан програми."""
        email = self.ids.email.text.strip()
        
        try:
            password = self.ids.password_field.ids.password_input.text.strip()
        except AttributeError:
            print(f"Помилка доступу до ID полів вводу в {self.__class__.__name__}")
            return
            
        msg_label = self.ids.login_message

        try:
            cursor.execute("SELECT id, username, password FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            
            if user and check_password(password, user[2]):
                user_id, username, _ = user
                app = App.get_running_app()
                
                app.current_user = username
                app.current_user_id = user_id

                cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (user_id,))
                result = cursor.fetchone()
                
                if result:
                    balance = result[0]
                else:
                    cursor.execute("INSERT INTO wallets (user_id, balance) VALUES (?, ?)", (user_id, 0.0))
                    conn.commit()
                    balance = 0.0

                app.balance = balance
                
                msg_label.text = f"Успішний вхід: {username}, баланс: ${balance:.2f}"
                
                self.ids.email.text = ""
                self.ids.password_field.ids.password_input.text = ""

                self.manager.transition.direction = 'left'
                self.manager.current = "dashboard_screen"
                
                Clock.schedule_once(lambda dt: self.force_dashboard_update(), 0.1)
                
            else:
                msg_label.text = "Невірна електронна адреса або пароль"
        except Exception as e:
            msg_label.text = f"Помилка входу: {str(e)}"
            print(f"Login error: {traceback.format_exc()}")

    def force_dashboard_update(self):
        """Примусово оновлює Dashboard, викликаючи метод оновлення у ньому."""
        dashboard = self.manager.get_screen('dashboard_screen')
        
        if hasattr(dashboard, 'update_all_tabs'):
            dashboard.update_all_tabs()
        elif 'home_tab' in dashboard.ids and hasattr(dashboard.ids.tab_manager.get_screen('home_tab'), 'update_content'):
            dashboard.ids.tab_manager.get_screen('home_tab').update_content()