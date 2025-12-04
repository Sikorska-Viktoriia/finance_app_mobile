import shutil
import os
import json
import csv
from datetime import datetime, timedelta
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle, Ellipse
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, StringProperty, ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform  # <--- ДОДАНО: Для перевірки платформи
import math
import traceback
from typing import Optional, Dict, Any, List, Callable, Tuple

# --- ІМПОРТ З utils.db_manager ---
try:
    from utils.db_manager import (
        cursor, conn, save_profile_photo, get_profile_photo, 
        log_user_session, get_login_history, get_user_settings, 
        update_user_settings, get_user_level, update_user_experience,
        log_security_action, get_user_by_email, check_password, 
        hash_password, get_total_balance, get_user_cards, get_user_envelopes,
        get_user_savings_plans, get_user_transactions, get_analytics_data,
        get_category_breakdown, get_top_categories, get_budget_progress,
        log_user_logout, create_envelope, add_to_envelope, safe_color_conversion, update_envelope
    )
    DB_MANAGER_AVAILABLE = True

    # --- ІМПОРТ PLYER ТА PARTIAL ДЛЯ ДОЗВОЛІВ ---
    try:
        from plyer import permissions
        from functools import partial
        PLYER_AVAILABLE = True
    except ImportError:
        PLYER_AVAILABLE = False
    # --------------------------------

except ImportError:
    # --- MOCK-ЛОГІКА ДЛЯ ЗАГЛУШКИ ---
    class MockCursor:
        def execute(self, *args): pass
        def fetchall(self): return []
        def fetchone(self): return None
    cursor = MockCursor()
    conn = None
    log_user_session = lambda *args: None
    log_user_logout = lambda *args: None
    get_total_balance = lambda *args: 0.0
    get_user_level = lambda *args: {'level': 1, 'experience': 0, 'next_level_xp': 100, 'progress_percentage': 0, 'achievements': []}
    check_password = lambda *args: False
    hash_password = lambda p: p
    save_profile_photo = lambda *args: True
    get_profile_photo = lambda *args: None
    get_login_history = lambda *args: []
    log_security_action = lambda *args: None
    create_envelope = lambda *args: None
    add_to_envelope = lambda *args: None
    update_envelope = lambda *args: True
    safe_color_conversion = lambda c: c if isinstance(c, list) else [0.2, 0.4, 0.8, 1]
    DB_MANAGER_AVAILABLE = False
    PLYER_AVAILABLE = False


# КРИТИЧНЕ ВИПРАВЛЕННЯ: Додано LIGHT_PINK
PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1) # <-- ВИПРАВЛЕНО NameError
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WARNING_ORANGE = (1, 0.6, 0.2, 1)
SAVINGS_PINK = (0.95, 0.4, 0.6, 1) 
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
MEDIUM_GRAY = (0.7, 0.7, 0.7, 1)
DARK_GRAY = (0.4, 0.4, 0.4, 1)

ENVELOPE_COLORS = [
    [0.95, 0.3, 0.5, 1], [0.2, 0.7, 0.9, 1], [0.2, 0.8, 0.3, 1], [1.0, 0.6, 0.2, 1],
    [0.6, 0.2, 0.8, 1], [0.2, 0.8, 0.8, 1], [0.9, 0.2, 0.2, 1], [0.4, 0.2, 0.9, 1],
    [1.0, 0.8, 0.2, 1], [0.8, 0.4, 0.9, 1], [0.3, 0.8, 0.6, 1], [0.9, 0.5, 0.7, 1],
    [0.5, 0.5, 0.9, 1], [0.9, 0.7, 0.3, 1], [0.7, 0.9, 0.4, 1], [0.8, 0.6, 0.9, 1],
]

def get_unique_color(envelope_count):
    return ENVELOPE_COLORS[envelope_count % len(ENVELOPE_COLORS)]


# --- ДОПОМІЖНІ ВІДЖЕТИ ---

class WhitePopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = [0, 0, 0, 0.1] 
        self.background = '' 
        self.separator_height = 0
        self.auto_dismiss = False

class WhiteButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = kwargs.get('background_color', PRIMARY_BLUE)
        self.color = kwargs.get('color', WHITE)
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(45)
        self.bold = True
        
        with self.canvas.before:
            Color(*self.background_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(background_color=self._update_color)
    
    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def _update_color(self, instance, value):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*value)
            self.rect = Rectangle(pos=self.pos, size=self.size)

class PasswordTextInput(TextInput):
    visibility_icon = StringProperty("eye-off")
    
    def __init__(self, **kwargs):
        kwargs.pop('password', None)
        super().__init__(**kwargs)
        
        self.multiline = False
        self.padding = [dp(15), dp(12), dp(50), dp(12)]
        self.password = True
        self.visibility_icon = "eye-off"
        
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

    def toggle_password(self):
        self.password = not self.password
        self.visibility_icon = "eye" if not self.password else "eye-off"
        self.focus = True

class WhiteTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.padding = [dp(15), dp(12)]
        
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

class CompactEnvelopeCard(BoxLayout):

    def __init__(self, envelope_data, on_manage_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.envelope_data = envelope_data
        self.on_manage_callback = on_manage_callback
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = dp(130)
        self.padding = dp(12)
        self.spacing = dp(6)
        
        color_tuple = safe_color_conversion(envelope_data['color'])

        with self.canvas.before:
            Color(*color_tuple)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
     
            Color(1, 1, 1, 0.2)
            self.overlay_rect = RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.4),
                size=(self.width, self.height * 0.6),
                radius=[dp(12)]
            )
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
        name_label = Label(text=envelope_data['name'], font_size=dp(14), bold=True, color=WHITE, size_hint_y=None, height=dp(22))
        self.add_widget(name_label)
        
        balance_label = Label(text=f"{envelope_data['current_amount']:.2f} $", font_size=dp(18), bold=True, color=WHITE, size_hint_y=None, height=dp(26))
        self.add_widget(balance_label)
        
        if envelope_data['budget_limit'] > 0:
            self.progress_bg = Widget(size_hint_y=None, height=dp(6))
            with self.progress_bg.canvas:
                Color(1, 1, 1, 0.3)
                self.progress_bg_rect = Rectangle(pos=self.pos, size=self.size) # Використовуємо self.pos/size тут, потім прив'язка оновлює
            self.add_widget(self.progress_bg)
            
            percentage = min((envelope_data['current_amount'] / envelope_data['budget_limit']) * 100, 100)
            percent_label = Label(text=f"{percentage:.0f}%", font_size=dp(10), color=WHITE, size_hint_y=None, height=dp(16))
            self.add_widget(percent_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(5))
        add_btn = Button(text='+', size_hint_x=0.5, background_color=(1, 1, 1, 0.3), color=WHITE, font_size=dp(14), bold=True)
        add_btn.bind(on_press=self.on_add_money)
        buttons_layout.add_widget(add_btn)
        
        edit_btn = Button(text='✎', size_hint_x=0.5, background_color=(1, 1, 1, 0.2), color=WHITE, font_size=dp(12), bold=True)
        edit_btn.bind(on_press=self.on_edit)
        buttons_layout.add_widget(edit_btn)
        
        self.add_widget(buttons_layout)
        
        if hasattr(self, 'progress_bg'):
            self.progress_bg.bind(pos=self._update_progress_bg, size=self._update_progress_bg)

    def update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.overlay_rect.pos = (self.x, self.y + self.height * 0.4)
        self.overlay_rect.size = (self.width, self.height * 0.6)

    def _update_progress_bg(self, instance, value):
        self.progress_bg_rect.pos = instance.pos
        self.progress_bg_rect.size = instance.size
        self.update_progress_bar()

    def update_progress_bar(self):
        if not hasattr(self, 'progress_bg') or self.envelope_data['budget_limit'] <= 0: return
            
        # Очищаємо canvas.after progress_bg
        self.progress_bg.canvas.after.clear() 
        percentage = min((self.envelope_data['current_amount'] / self.envelope_data['budget_limit']) * 100, 100)
        
        with self.progress_bg.canvas.after:
            if percentage < 70: Color(*SUCCESS_GREEN)
            elif percentage < 90: Color(*WARNING_ORANGE)
            else: Color(*ERROR_RED)
                
            progress_width = self.progress_bg.width * (percentage / 100)
            RoundedRectangle(pos=self.progress_bg.pos, size=(progress_width, self.progress_bg.height), radius=[dp(3)])

    def on_add_money(self, instance):
        if self.on_manage_callback:
            self.on_manage_callback(self.envelope_data, 'add')

    def on_edit(self, instance):
        if self.on_manage_callback:
            self.on_manage_callback(self.envelope_data, 'edit')


class StatCard(BoxLayout):
    def __init__(self, title, value, subtitle="", color=PRIMARY_BLUE, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = dp(100)
        self.padding = dp(10)
        self.spacing = dp(4)
        
        with self.canvas.before:
            Color(*color)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        
        self.bind(pos=self._update, size=self._update)
        
        self.title_label = Label(text=title, font_size=dp(12), color=WHITE, bold=True, size_hint_y=None, height=dp(20))
        self.add_widget(self.title_label)
        
        self.value_label = Label(text=str(value), font_size=dp(16), color=WHITE, bold=True, size_hint_y=None, height=dp(26))
        self.add_widget(self.value_label)
        
        self.subtitle_label = Label(text=subtitle, font_size=dp(10), color=WHITE, size_hint_y=None, height=dp(16))
        self.add_widget(self.subtitle_label)
    
    def update_data(self, value, subtitle=""):
        self.value_label.text = str(value)
        self.subtitle_label.text = subtitle
    
    def _update(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size




class SimplePieChartWidget(Widget):
    """Кільцева діаграма (Donut Chart) без розділювальних ліній."""
    inner_radius_factor = 0.5 
    
    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.size_hint = (1, None)
        self.height = dp(250)
        
        self.sectors = []
        self.center_x = 0
        self.center_y = 0
        self.radius = 0
        self.inner_radius = 0
        self.VISUAL_OFFSET = 90 

        self.bind(pos=self.update_chart, size=self.update_chart)
    
    def update_data(self, data):
        self.data = data
        self.update_chart()
    
    def update_chart(self, *args):
        self.canvas.clear()
        for child in self.children[:]:
            self.remove_widget(child)
        
        if not self.data: self.show_no_data(); return
        
        total = sum(item['amount'] for item in self.data)
        if total == 0: self.show_no_data(); return
        
        self.center_x = self.width / 2
        self.center_y = self.height / 2
        self.radius = min(self.width, self.height) * 0.45 
        self.inner_radius = self.radius * self.inner_radius_factor
        
        start_angle_kivy = 0
        self.sectors = []
        
        for item in self.data:
            percentage = item['amount'] / total
            angle = percentage * 360
            end_angle_kivy = start_angle_kivy + angle
            
            self.draw_filled_sector(
                self.center_x, self.center_y, self.radius, 
                start_angle_kivy + self.VISUAL_OFFSET, 
                end_angle_kivy + self.VISUAL_OFFSET, 
                safe_color_conversion(item['color'])
            )
            
            self.sectors.append({
                'item': item,
                'percentage': percentage,
                'start_angle_kivy': start_angle_kivy, 
                'end_angle_kivy': end_angle_kivy,
                'color': safe_color_conversion(item['color'])
            })
            
            start_angle_kivy = end_angle_kivy
        
        self.draw_separators()

    def draw_filled_sector(self, cx, cy, radius, start_angle, end_angle, color):
        with self.canvas:
            Color(*color)
            Ellipse(
                pos=(cx - radius, cy - radius),
                size=(radius * 2, radius * 2),
                angle_start=start_angle,
                angle_end=end_angle
            )

    def draw_separators(self):
        """Малює лише біле внутрішнє коло, видаляючи чорні лінії-розділювачі."""
        with self.canvas:
  
            Color(*WHITE)
            Ellipse(
                pos=(self.center_x - self.inner_radius, self.center_y - self.inner_radius),
                size=(self.inner_radius * 2, self.inner_radius * 2)
            )
            

    def on_touch_move(self, touch): return False
    def on_touch_down(self, touch): return False
    def handle_touch(self, touch): return False
    def get_sector_at_pos(self, x, y): return None 
    
    def show_no_data(self):
        center_x = self.width / 2
        center_y = self.height / 2
        with self.canvas:
            Color(*LIGHT_GRAY)
            Ellipse(pos=(center_x - dp(40), center_y - dp(40)), size=(dp(80), dp(80)))
        no_data_label = Label(text="Немає даних\nдля відображення", pos=(center_x - dp(60), center_y - dp(20)), size=(dp(120), dp(40)), font_size=dp(12), color=DARK_GRAY, halign='center', valign='middle')
        self.add_widget(no_data_label)


class SimpleBarChartWidget(BoxLayout):
    """Віджет для відображення стовпчастої діаграми (витрати по днях за місяць)."""
    
    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(5)
        self.size_hint = (1, 1)
        self.bar_width_dp = dp(18)
        
        self.scroll_view = ScrollView(size_hint_y=0.9, do_scroll_y=False)
        self.chart_area = BoxLayout(orientation='horizontal', size_hint_y=1, spacing=dp(2))
        self.labels_area = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20), spacing=dp(2))
        
        self.scroll_view.add_widget(self.chart_area)
        self.add_widget(self.scroll_view)
        self.add_widget(self.labels_area)
        
        self.bind(size=self.update_chart)
        self.update_chart()

    def update_data(self, data):
        self.data = data
        self.update_chart()

    def update_chart(self, *args):
        self.chart_area.clear_widgets()
        self.labels_area.clear_widgets()

        if not self.data:
            self.chart_area.add_widget(Label(text="Немає даних за поточний місяць", color=DARK_GRAY))
            return

        amounts = [item['amount'] for item in self.data]
        dates = [item['date'] for item in self.data]
        
        max_amount = max(amounts) if amounts else 0
        if max_amount == 0: max_amount = 1 
        
        bar_width_dp = self.bar_width_dp
        total_width = len(self.data) * bar_width_dp + (len(self.data) - 1) * dp(2)
        
        self.chart_area.width = max(self.width - dp(20), total_width) 
        self.chart_area.size_hint_x = None 
        
        self.labels_area.width = self.chart_area.width 
        self.labels_area.size_hint_x = None
        
        for amount, date_str in zip(amounts, dates):
            bar_height_factor = amount / max_amount
            bar_color = ERROR_RED
            
            bar_container = BoxLayout(orientation='vertical', size_hint_x=None, width=bar_width_dp, spacing=dp(2))
            
            spacer = Widget(size_hint_y=1 - bar_height_factor)
            bar_container.add_widget(spacer)

            bar = Widget(size_hint_y=bar_height_factor)
            with bar.canvas:
                Color(*bar_color)
                bar.rect = Rectangle(pos=bar.pos, size=bar.size)
            
            bar.bind(pos=lambda instance, value: setattr(instance.rect, 'pos', value),
                     size=lambda instance, value: setattr(instance.rect, 'size', value))

            label_text = f"${amount:.0f}"
            value_label = Label(
                text=label_text, 
                color=DARK_TEXT, 
                size_hint_y=None, 
                height=dp(15),
                font_size=dp(8)
            )
            bar_container.add_widget(value_label)
            bar_container.add_widget(bar)
            self.chart_area.add_widget(bar_container)

            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                day_num = date_obj.strftime('%d')
            except ValueError:
                day_num = date_str 
                
            date_label = Label(
                text=day_num,
                size_hint_x=None,
                width=bar_width_dp, 
                color=DARK_TEXT,
                font_size=dp(10)
            )
            self.labels_area.add_widget(date_label)
        
        self.scroll_view.unbind(scroll_x=self._update_labels_scroll)
        self.scroll_view.fbind('scroll_x', self._update_labels_scroll)
    
    def _update_labels_scroll(self, instance, value):
        """Синхронізує горизонтальну позицію міток із прокруткою."""
        max_scroll = self.chart_area.width - self.scroll_view.width
        scroll_offset_x = -value * max_scroll
        
    
        self.labels_area.x = self.scroll_view.x + scroll_offset_x


class AccountTab(Screen):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_session_id = None
        self.profile_photos_dir = "profile_photos"
        
        if not os.path.exists(self.profile_photos_dir):
            os.makedirs(self.profile_photos_dir)

    def on_enter(self):
        app = App.get_running_app()
        if hasattr(app, 'current_user_id') and app.current_user_id:
            self.log_session_start()
            self.update_account_tab()
        else:
            self.show_unauthorized_state()

    def on_leave(self):
        self.log_session_end()

    def log_session_start(self):
        try:
            app = App.get_running_app()
            if DB_MANAGER_AVAILABLE and hasattr(app, 'current_user_id') and app.current_user_id:
                device_info = f"{Window.width}x{Window.height}"
                self.current_session_id = log_user_session(cursor, conn, app.current_user_id, device_info, "127.0.0.1")
        except Exception as e:
            print(f"Помилка логування сесії: {e}")

    def log_session_end(self):
        try:
            if DB_MANAGER_AVAILABLE and self.current_session_id:
                log_user_logout(cursor, conn, self.current_session_id)
        except Exception as e:
            print(f"Помилка логування кінця сесії: {e}")

    def update_account_tab(self):
        try:
            app = App.get_running_app()
            
            if not DB_MANAGER_AVAILABLE or not hasattr(app, 'current_user_id') or not app.current_user_id:
                self.show_unauthorized_state()
                return
            
            user_data = cursor.execute("SELECT username, email, created_at FROM users WHERE id=?", (app.current_user_id,)).fetchone()
            
            if user_data:
                username, email, created_at = user_data
                
                self.ids.username_label.text = f"{username}"
                self.ids.email_label.text = f"{email}"
                
                total_balance = get_total_balance(cursor, app.current_user_id)
                self.ids.balance_label.text = f"${total_balance:.2f}"
                
                if created_at:
                    reg_date = created_at.split()[0] if ' ' in created_at else created_at
                    self.ids.registration_label.text = f"З нами з: {reg_date}"
                
                level_info = get_user_level(cursor, app.current_user_id)
                self.ids.status_label.text = f"Рівень {level_info['level']} • {level_info['experience']} XP"
                
                login_history = get_login_history(cursor, app.current_user_id, 1)
                if login_history:
                    last_login = login_history[0]['login_time'].split()[0]
                    self.ids.last_login_label.text = f"Останній вхід: {last_login}"
                else:
                    self.ids.last_login_label.text = "Останній вхід: сьогодні"
                
                self.load_profile_photo()
            else:
                self.show_unauthorized_state()
                
        except Exception as e:
            print(f"Помилка оновлення акаунту: {traceback.format_exc()}")
            self.show_error_state()

    def load_profile_photo(self):
        """Завантажити фото з підтримкою Android"""
        try:
            app = App.get_running_app()
            if hasattr(app, 'current_user_id') and app.current_user_id:
                photo_path = get_profile_photo(cursor, app.current_user_id)
                
                if photo_path and os.path.exists(photo_path):
                    self.ids.profile_image.source = photo_path
                else:
                    self.ids.profile_image.source = "assets/icons/default_avatar.png"
            else:
                self.ids.profile_image.source = "assets/icons/default_avatar.png"
        except Exception as e:
            print(f"Помилка завантаження фото: {e}")
            self.ids.profile_image.source = "assets/icons/default_avatar.png"

  

    def _open_file_chooser_popup(self):
        """
        Фактично відкриває FileChooser у Popup. 
        Викликається лише після успішної перевірки дозволу на Android.
        """
        try:
            content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
            
            title_label = Label(text="Оберіть фото профілю", size_hint_y=None, height=dp(40), color=DARK_TEXT, font_size=dp(18), bold=True)
            content.add_widget(title_label)
            
      
            start_path = '/storage/emulated/0/' if platform == 'android' else os.getcwd() 
            
            filechooser = FileChooserListView(filters=['*.png', '*.jpg', '*.jpeg'], path=start_path)
            content.add_widget(filechooser)
            
            btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            btn_select = WhiteButton(text='Вибрати', background_color=PRIMARY_PINK)
            btn_cancel = WhiteButton(text='Скасувати', background_color=LIGHT_GRAY, color=DARK_TEXT)
            
            def select_photo(instance):
                if filechooser.selection:
                    selected_file = filechooser.selection[0]
                    if self._process_profile_photo(selected_file):
                        popup.dismiss()
                    else:
                        self.show_message("Помилка при обробці фото")
                else:
                    self.show_message("Виберіть файл")
            
            btn_select.bind(on_press=select_photo)
            btn_cancel.bind(on_press=lambda x: popup.dismiss())
            
            btn_layout.add_widget(btn_select)
            btn_layout.add_widget(btn_cancel)
            content.add_widget(btn_layout)
            
            popup = WhitePopup(title='Виберіть фото профілю', content=content, size_hint=(0.9, 0.9))
            popup.open()
            
        except Exception as e:
            print(f"Помилка відкриття вибору фото: {traceback.format_exc()}")
            self.show_message("Помилка при виборі фото")

    def _handle_permission_result(self, callback_func, permission_result, *args):
        """Обробляє відповідь користувача на запит дозволів."""
        if permission_result.get('android.permission.READ_EXTERNAL_STORAGE') == 'granted':
           
            callback_func()
        else:
            self.show_message("Дозвіл на читання сховища відхилено. Неможливо вибрати зовнішні файли.")


    def change_profile_photo(self):
        """
        [ОНОВЛЕНО] Перевіряє дозвіл READ_EXTERNAL_STORAGE перед відкриттям FileChooser.
        """
        if platform == 'android' and PLYER_AVAILABLE:
            try:
                if permissions.check('android.permission.READ_EXTERNAL_STORAGE'):
                    self._open_file_chooser_popup()
                    return
                
        
                permissions.request_permissions(
                    ['android.permission.READ_EXTERNAL_STORAGE'],
                    callback=partial(self._handle_permission_result, self._open_file_chooser_popup)
                )
            except Exception as e:
               
                print(f"Помилка запиту дозволу на Android: {e}")
                self.show_message("Помилка при запиті дозволів. Спробуйте оновити додаток.")
                
        else:
       
            self._open_file_chooser_popup()

    def _process_profile_photo(self, file_path):
        """Обробити та зберегти фото профілю."""
        try:
            app = App.get_running_app()
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                return False
            
            if save_profile_photo(cursor, conn, app.current_user_id, file_path):
                self.ids.profile_image.reload()
                self.load_profile_photo()
                self.show_message("Фото профілю оновлено!")
                return True
            
            return False
            
        except Exception as e:
            print(f"Помилка обробки фото: {traceback.format_exc()}")
            self.show_message(f"Помилка обробки фото: {e}")
            return False


    def delete_account(self):
        """Показує підтвердження видалення акаунта."""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        content.add_widget(Label(
            text='Ця дія НЕЗВОРОТНА!\n\n' +
                 'Видаляться всі ваші дані:\n' +
                 '• Картки та транзакції\n' +
                 '• Конверти та плани\n' +
                 '• Вся історія та статистика\n\n' +
                 'Для підтвердження введіть пароль:',
            color=DARK_TEXT,
            text_size=(dp(400), None)
        ))
        
        password_input = PasswordTextInput(hint_text='Введіть ваш пароль')
        content.add_widget(password_input)
        
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_confirm = WhiteButton(text='Видалити акаунт', background_color=ERROR_RED)
        btn_cancel = WhiteButton(text='Скасувати', background_color=LIGHT_GRAY, color=DARK_TEXT)
        
        def confirm_delete(instance):
            password = password_input.text.strip()
            if password and self.verify_password_for_deletion(password):
                self.perform_account_deletion()
                popup.dismiss()
            else:
                self.show_message("Невірний пароль або поле пусте")
        
        btn_confirm.bind(on_press=confirm_delete)
        btn_cancel.bind(on_press=lambda x: popup.dismiss())
        
        btn_layout.add_widget(btn_confirm)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        
        popup = WhitePopup(title='Видалення акаунта', content=content, size_hint=(0.8, 0.6))
        popup.open()

    def verify_password_for_deletion(self, password):
        """Перевіряє пароль користувача для критичних дій."""
        try:
            app = App.get_running_app()
            cursor.execute("SELECT password FROM users WHERE id=?", (app.current_user_id,))
            result = cursor.fetchone()
            if result:
                return check_password(password, result[0])
            return False
        except Exception as e:
            print(f"Помилка верифікації пароля: {e}")
            return False

    def perform_account_deletion(self):
        """Видаляє всі дані користувача з бази даних."""
        try:
            app = App.get_running_app()
            user_id = app.current_user_id
            
            log_security_action(cursor, conn, user_id, "account_deletion", "Користувач видалив акаунт")
            
            tables = [
                'envelope_transactions', 'envelopes', 'savings_transactions', 
                'savings_plans', 'transactions', 'user_cards', 'security_logs', 
                'user_sessions', 'user_settings', 'user_levels', 'user_profile_photos', 'wallets' 
            ]
            
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
                except Exception as e:
                    print(f"Помилка видалення з {table}: {e}")
            
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            
            self.cleanup_profile_photos(user_id) 
            
            app.current_user = ""
            app.current_user_id = 0
            app.balance = 0.0
            
            app.root.current = "login_screen"
            app.root.transition.direction = 'right'
            
            self.show_message("Акаунт успішно видалено")
            
        except Exception as e:
            print(f"Помилка видалення акаунта: {e}")
            self.show_message("Помилка при видаленні акаунта")

    def cleanup_profile_photos(self, user_id):
        """Видаляє локальні файли фотографій профілю, пов'язані з user_id."""
        try:
            for filename in os.listdir(self.profile_photos_dir):
                if filename.startswith(f"profile_{user_id}_"):
                    file_path = os.path.join(self.profile_photos_dir, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Помилка очищення фото: {e}")

    def show_login_history(self):
        """Показує історію входів з прокруткою."""
        try:
            app = App.get_running_app()
            sessions = get_login_history(cursor, app.current_user_id, 20)
            
            content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
            
            content.add_widget(Label(text='Історія входів', size_hint_y=None, height=dp(40), bold=True, color=PRIMARY_PINK, font_size=dp(18)))
            
            scroll_content = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
            scroll_content.bind(minimum_height=scroll_content.setter('height'))
            
            if not sessions:
                scroll_content.add_widget(Label(text='Історія входів відсутня', size_hint_y=None, height=dp(40), color=DARK_TEXT))
            else:
                for session in sessions:
                    session_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80), padding=dp(10))
                    
                    with session_layout.canvas.before:
                        Color(0.95, 0.95, 0.95, 1)
                        session_layout.rect = Rectangle(pos=session_layout.pos, size=session_layout.size)
                    
                    session_layout.bind(pos=self._update_session_rect, size=self._update_session_rect)
                    
                    device_label = Label(text=f" {session['device']}", size_hint_y=None, height=dp(25), text_size=(dp(450), None), color=DARK_TEXT, halign='left', valign='middle')
                    ip_label = Label(text=f" IP: {session['ip']}", size_hint_y=None, height=dp(20), text_size=(dp(450), None), color=DARK_GRAY, font_size=dp(12), halign='left', valign='middle')
                    
                    time_text = f" Вхід: {session['login_time']}"
                    if session['logout_time']:
                        time_text += f" | Тривалість: {session['duration']}"
                    else:
                        time_text += " | Активна сесія"
                    
                    time_label = Label(text=time_text, size_hint_y=None, height=dp(25), font_size=dp(12), text_size=(dp(450), None), color=DARK_GRAY, halign='left', valign='middle')
                    
                    session_layout.add_widget(device_label)
                    session_layout.add_widget(ip_label)
                    session_layout.add_widget(time_label)
                    scroll_content.add_widget(session_layout)
            
            scrollview = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, scroll_type=['bars', 'content'], bar_width=dp(10), bar_color=[0.7, 0.7, 0.7, 0.8])
            scrollview.add_widget(scroll_content)
            content.add_widget(scrollview)
            
            btn_close = WhiteButton(text='Закрити', size_hint_y=None, height=dp(50), background_color=PRIMARY_BLUE)
            btn_close.bind(on_press=lambda x: popup.dismiss())
            content.add_widget(btn_close)
            
            popup = WhitePopup(title='Історія входів', content=content, size_hint=(0.95, 0.8), auto_dismiss=True)
            popup.open()
            
        except Exception as e:
            print(f"Помилка показу історії: {e}")
            self.show_message("Помилка завантаження історії входів")

    def _update_session_rect(self, instance, value):
        if hasattr(instance, 'rect'):
            instance.rect.pos = instance.pos
            instance.rect.size = instance.size

    def edit_profile(self):
        try:
            app = App.get_running_app()
          
            cursor.execute("SELECT username, email FROM users WHERE id=?", (app.current_user_id,)).fetchone()
            user_data = cursor.fetchone() 
            
            content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
            
            content.add_widget(Label(text='Ім\'я:', color=DARK_TEXT))
            username_input = WhiteTextInput(text=user_data[0] if user_data else '')
            content.add_widget(username_input)
            
            content.add_widget(Label(text='Email:', color=DARK_TEXT))
            email_input = WhiteTextInput(text=user_data[1] if user_data else '')
            content.add_widget(email_input)
            
            content.add_widget(Label(text='Зміна пароля (за бажанням):', color=DARK_TEXT))
            
            current_password_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(70))
            current_password_layout.add_widget(Label(text='Поточний пароль:', size_hint_y=None, height=dp(25), color=DARK_TEXT))
            current_password_input = PasswordTextInput(hint_text='Введіть поточний пароль')
            current_password_layout.add_widget(current_password_input)
            content.add_widget(current_password_layout)
            
            new_password_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(70))
            new_password_layout.add_widget(Label(text='Новий пароль:', size_hint_y=None, height=dp(25), color=DARK_TEXT))
            new_password_input = PasswordTextInput(hint_text='Введіть новий пароль')
            new_password_layout.add_widget(new_password_input)
            content.add_widget(new_password_layout)
            
            confirm_password_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(70))
            confirm_password_layout.add_widget(Label(text='Підтвердіть новий пароль:', size_hint_y=None, height=dp(25), color=DARK_TEXT))
            confirm_password_input = PasswordTextInput(hint_text='Підтвердіть новий пароль')
            confirm_password_layout.add_widget(confirm_password_input)
            content.add_widget(confirm_password_layout)
            
            btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            btn_save = WhiteButton(text='Зберегти', background_color=PRIMARY_PINK)
            btn_cancel = WhiteButton(text='Скасувати', background_color=LIGHT_GRAY, color=DARK_TEXT)
            
            def save_profile(instance):
                new_username = username_input.text.strip()
                new_email = email_input.text.strip()
                current_password = current_password_input.text
                new_password = new_password_input.text
                confirm_password = confirm_password_input.text
                
                if not new_username or not new_email:
                    self.show_message("Заповніть обов'язкові поля")
                    return
                
                password_change = bool(current_password or new_password or confirm_password)
                if password_change:
                    if not current_password: self.show_message("Введіть поточний пароль"); return
                    if not new_password: self.show_message("Введіть новий пароль"); return
                    if new_password != confirm_password: self.show_message("Нові паролі не співпадають"); return
                    if len(new_password) < 6: self.show_message("Новий пароль має містити принаймні 6 символів"); return
                
                self.update_user_profile(new_username, new_email, current_password, new_password)
                popup.dismiss()
            
            btn_save.bind(on_press=save_profile)
            btn_cancel.bind(on_press=lambda x: popup.dismiss())
            
            btn_layout.add_widget(btn_save)
            btn_layout.add_widget(btn_cancel)
            content.add_widget(btn_layout)
            
            popup = WhitePopup(title='Редагування профілю', content=content, size_hint=(0.9, 0.9))
            popup.open()
            
        except Exception as e:
            print(f"Помилка редагування профілю: {e}")
            self.show_message("Помилка відкриття редактора")

    def update_user_profile(self, username, email, current_password=None, new_password=None):
        try:
            app = App.get_running_app()
            
            if current_password and new_password:
                cursor.execute("SELECT password FROM users WHERE id=?", (app.current_user_id,))
                result = cursor.fetchone()
                if not result or not check_password(current_password, result[0]):
                    self.show_message("Невірний поточний пароль")
                    return
            
            update_fields = ["username=?", "email=?", "updated_at=CURRENT_TIMESTAMP"]
            params = [username, email]
            
            if new_password:
                update_fields.append("password=?")
                params.append(hash_password(new_password))
            
            params.append(app.current_user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
            cursor.execute(query, params)
            conn.commit()
            
            app.current_user = username
            
            action_desc = "Оновлено профіль"
            if new_password: action_desc += " зі зміною пароля"
            log_security_action(cursor, conn, app.current_user_id, "profile_updated", action_desc)
            
            self.update_account_tab()
            self.show_message("Профіль успішно оновлено!")
            
            update_user_experience(cursor, conn, app.current_user_id, 5)
            
        except Exception as e:
            print(f"Помилка оновлення профілю: {e}")
            self.show_message("Помилка при оновленні профілю")

    def download_user_data(self):
   
        try:
            app = App.get_running_app()
            exports_dir = "user_exports"
         
            if not os.path.exists(exports_dir):
                os.makedirs(exports_dir)
            filename = f"financial_data_{app.current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(exports_dir, filename)
            
            self.create_text_report(filepath, app.current_user_id, app.current_user)
            
            log_security_action(cursor, conn, app.current_user_id, "data_export", "Користувач експортував дані")
            
            self.show_message(f"Дані експортовано:\n{filename}")
            
        except Exception as e:
            print(f"Помилка експорту: {e}")
            self.show_message("Помилка при експорті даних")

    def create_text_report(self, filepath, user_id, username):
     
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"ФІНАНСОВИЙ ЗВІТ - {username}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Дата експорту: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("ОСНОВНА ІНФОРМАЦІЯ:\n")
                f.write("-" * 40 + "\n")
                cursor.execute("SELECT username, email, created_at FROM users WHERE id=?", (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    f.write(f"Ім'я: {user_data[0]}\n")
                    f.write(f"Email: {user_data[1]}\n")
                    f.write(f"Дата реєстрації: {user_data[2]}\n")
                
                total_balance = get_total_balance(cursor, user_id)
                f.write(f"Загальний баланс: ${total_balance:.2f}\n\n")
                
                cards = get_user_cards(cursor, user_id)
                f.write("КАРТКИ:\n")
                f.write("-" * 40 + "\n")
                if cards:
                    for card in cards:
                        f.write(f"• {card['name']} ({card['bank']}): ${card['balance']:.2f}\n")
                else:
                    f.write("Картки відсутні\n")
                f.write("\n")
                
                envelopes = get_user_envelopes(cursor, user_id)
                f.write("КОНВЕРТИ:\n")
                f.write("-" * 40 + "\n")
                if envelopes:
                    for env in envelopes:
                        f.write(f"• {env['name']}: ${env['current_amount']:.2f}/${env['budget_limit']:.2f} ({env['usage_percentage']:.1f}%)\n")
                else:
                    f.write("Конверти відсутні\n")
                f.write("\n")
                
                savings = get_user_savings_plans(cursor, user_id)
                f.write("ПЛАНИ ЗАОЩАДЖЕНЬ:\n")
                f.write("-" * 40 + "\n")
                if savings:
                    for plan in savings:
                        f.write(f"• {plan['name']}: ${plan['current_amount']:.2f}/${plan['target_amount']:.2f} ({plan['progress_percentage']:.1f}%)\n")
                else:
                    f.write("Плани заощаджень відсутні\n")
                f.write("\n")
                
                f.write("АНАЛІТИКА ЗА МІСЯЦЬ:\n")
                f.write("-" * 40 + "\n")
                analytics = get_analytics_data(cursor, user_id, 'month')
                if analytics:
                    f.write(f"Доходи: ${analytics['total_income']:.2f}\n")
                    f.write(f"Витрати: ${analytics['total_expenses']:.2f}\n")
                    f.write(f"Чистий баланс: ${analytics['net_balance']:.2f}\n")
                    f.write(f"Середні витрати/день: ${analytics['average_daily']:.2f}\n")
                    f.write(f"Транзакції: {analytics['transactions_count']}\n")
                    f.write(f"Рівень заощаджень: {analytics['savings_rate']:.1f}%\n\n")
                
                top_categories = get_top_categories(cursor, user_id, 'month', 5)
                f.write("ТОП КАТЕГОРІЇ ВИТРАТ:\n")
                f.write("-" * 40 + "\n")
                if top_categories:
                    for cat in top_categories:
                        f.write(f"• {cat['name']}: ${cat['amount']:.2f} ({cat['value']:.1f}%)\n")
                else:
                    f.write("Дані про категорії відсутні\n")
                f.write("\n")
                
                transactions = get_user_transactions(cursor, user_id, 10)
                f.write("ОСТАННІ ТРАНЗАКЦІЇ:\n")
                f.write("-" * 40 + "\n")
                if transactions:
                    for trans in transactions:
                        amount_str = f"${trans['amount']:.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):.2f}"
                        f.write(f"• {trans['date'][:10]} | {trans['type']} | {amount_str} | {trans['description']}\n")
                else:
                    f.write("Транзакції відсутні\n")
                f.write("\n")
                
                f.write("=" * 60 + "\n")
                f.write("Звіт створено автоматично системою Financial Assistant\n")
                f.write("Усі дані захищено та конфіденційно\n")
                f.write("=" * 60 + "\n")
                
        except Exception as e:
            print(f"Помилка створення звіту: {e}")
            raise

    def show_level_info(self):

        try:
            app = App.get_running_app()
            level_info = get_user_level(cursor, app.current_user_id)
            
            content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
            
            content.add_widget(Label(text=f'Рівень: {level_info["level"]}', font_size=dp(20), bold=True, size_hint_y=None, height=dp(40), color=PRIMARY_PINK))
            
            progress_layout = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None, height=dp(60))
            progress_layout.add_widget(Label(text=f'Прогрес: {level_info["experience"]}/{level_info["next_level_xp"]} XP', size_hint_y=None, height=dp(20), color=DARK_TEXT))
            
            progress_bar = ProgressBar(max=100, value=level_info['progress_percentage'], size_hint_y=None, height=dp(20))
            progress_layout.add_widget(progress_bar)
            content.add_widget(progress_layout)
            
            achievements = level_info['achievements']
            if achievements:
                content.add_widget(Label(text='Досягнення:', size_hint_y=None, height=dp(30), bold=True, color=DARK_TEXT))
                for achievement in achievements:
                    content.add_widget(Label(text=f"• {achievement}", size_hint_y=None, height=dp(25), color=DARK_TEXT))
            else:
                content.add_widget(Label(text='Ще немає досягнень', size_hint_y=None, height=dp(30), color=DARK_GRAY))
            
            content.add_widget(Label(text='\nЯк отримати XP:\n• Додавання транзакцій: +1 XP\n• Створення картки: +5 XP\n• Оновлення профілю: +5 XP', size_hint_y=None, height=dp(100), color=DARK_TEXT))
            
            btn_close = WhiteButton(text='Закрити', background_color=PRIMARY_BLUE)
            btn_close.bind(on_press=lambda x: popup.dismiss())
            content.add_widget(btn_close)
            
            popup = WhitePopup(title='Рівень та досягнення', content=content, size_hint=(0.8, 0.7))
            popup.open()
            
        except Exception as e:
            print(f"Помилка показу інформації про рівень: {e}")


    def logout(self):
        """Виконує безпечний вихід користувача."""
        try:
            app = App.get_running_app()
            log_security_action(cursor, conn, app.current_user_id, "logout", "Користувач вийшов з системи")
            self.log_session_end()
            
            app.current_user = ""
            app.current_user_id = 0
            app.balance = 0.0
            
            app.root.current = "login_screen"
            app.root.transition.direction = 'right'
            
        except Exception as e:
            print(f"Помилка при виході: {e}")

    def refresh_account(self):
        self.update_account_tab()
        app = App.get_running_app()
        update_user_experience(cursor, conn, app.current_user_id, 1)
        
        self.ids.refresh_button.opacity = 0.7
        Clock.schedule_once(self.reset_refresh_button, 0.5)
    
    def reset_refresh_button(self, dt):
        self.ids.refresh_button.opacity = 1

    def show_unauthorized_state(self):
        self.ids.username_label.text = "Не авторизовано"
        self.ids.email_label.text = "Не доступно"
        self.ids.balance_label.text = "$0.00"
        self.ids.registration_label.text = "Не доступно"
        self.ids.status_label.text = "Не авторизовано"
        self.ids.last_login_label.text = "Не доступно"
        self.ids.profile_image.source = "assets/icons/default_avatar.png"

    def show_error_state(self):
        self.ids.username_label.text = "Помилка"
        self.ids.email_label.text = "Помилка"
        self.ids.balance_label.text = "Помилка"
        self.ids.registration_label.text = "Помилка"
        self.ids.status_label.text = "Помилка"
        self.ids.last_login_label.text = "Помилка"
        self.ids.profile_image.source = "assets/icons/default_avatar.png"

    def show_message(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        
        content.add_widget(Label(text=message, color=DARK_TEXT, text_size=(dp(350), None)))
        
        btn_ok = WhiteButton(text='OK', background_color=PRIMARY_BLUE)
        btn_ok.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(btn_ok)
        
        popup = WhitePopup(title='Повідомлення', content=content, size_hint=(0.7, 0.3))
        popup.open()