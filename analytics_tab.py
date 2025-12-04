from datetime import datetime, timedelta
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.properties import ListProperty, NumericProperty, StringProperty, ObjectProperty
# Явно імпортуємо всі потрібні UIX класи
from kivy.uix.button import Button 
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
import math
import json
import traceback
from typing import Optional, Dict, Any, List, Callable, Tuple

# --- Імпорт з utils ---
from utils.db_manager import (
    conn, cursor, get_user_envelopes, create_envelope, add_to_envelope,
    get_user_cards, get_envelope_transactions, get_envelope_stats,
    get_analytics_data, get_category_breakdown, get_top_categories,
    get_cards_analytics, get_budget_progress, get_insights_and_forecasts,
    get_monthly_comparison, update_envelope, safe_color_conversion
)
from utils.widgets import WhitePopup, WhiteButton, WhiteTextInput

# --- КОНСТАНТИ КОЛЬОРУ ---
PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1)
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
        self.hint_text_color = LIGHT_GRAY
        self.write_tab = False
        
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
                self.progress_bg_rect = Rectangle(pos=self.progress_bg.pos, size=self.progress_bg.size)
            self.add_widget(self.progress_bg)
            
            percentage = min((envelope_data['current_amount'] / envelope_data['budget_limit']) * 100, 100)
            percent_label = Label(text=f"{percentage:.0f}%", font_size=dp(10), color=WHITE, size_hint_y=None, height=dp(16))
            self.add_widget(percent_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(5))
        add_btn = Button(text='+', size_hint_x=0.5, background_color=(1, 1, 1, 0.3), color=WHITE, font_size=dp(14), bold=True)
        add_btn.bind(on_press=self.on_add_money)
        buttons_layout.add_widget(add_btn)
        
        edit_btn = Button(text='<>', size_hint_x=0.5, background_color=(1, 1, 1, 0.2), color=WHITE, font_size=dp(12), bold=True)
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
            
        self.canvas.after.clear()
        percentage = min((self.envelope_data['current_amount'] / self.envelope_data['budget_limit']) * 100, 100)
        
        with self.canvas.after:
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
            # 1. Біле внутрішнє коло (Доннат)
            Color(*WHITE)
            Ellipse(
                pos=(self.center_x - self.inner_radius, self.center_y - self.inner_radius),
                size=(self.inner_radius * 2, self.inner_radius * 2)
            )
            # Чорні розділювальні лінії ВИДАЛЕНО.
    
    # Вимкнена логіка торкання
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
        self.bar_width_dp = dp(18) # Фіксована ширина стовпця
        
        self.scroll_view = ScrollView(size_hint_y=0.9, do_scroll_y=False)
        self.chart_area = BoxLayout(orientation='horizontal', size_hint_y=1, spacing=dp(2))
        # ВИПРАВЛЕНО: Додано spacing для labels_area
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
        
        # Забезпечуємо прокручуваність області
        self.chart_area.width = max(self.width - dp(20), total_width) 
        self.chart_area.size_hint_x = None 
        
        # ВИПРАВЛЕНО: Синхронізуємо ширину області міток
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
                
            # ВИПРАВЛЕНО: Ширина мітки дорівнює ширині стовпця (без зовнішнього spacing)
            date_label = Label(
                text=day_num,
                size_hint_x=None,
                width=bar_width_dp, 
                color=DARK_TEXT,
                font_size=dp(10)
            )
            self.labels_area.add_widget(date_label)
        
        # Надійна прив'язка для синхронізації прокрутки
        self.scroll_view.unbind(scroll_x=self._update_labels_scroll)
        self.scroll_view.fbind('scroll_x', self._update_labels_scroll)
    
    def _update_labels_scroll(self, instance, value):
        """Синхронізує горизонтальну позицію міток із прокруткою."""
        # Max Scroll amount (in pixels)
        max_scroll = self.chart_area.width - self.scroll_view.width
        # Поточний зсув (від 0)
        scroll_offset_x = -value * max_scroll
        
        # Встановлюємо позицію X для області міток, щоб вона прокручувалася разом із барами
        # Використовуємо self.scroll_view.x як базову точку
        self.labels_area.x = self.scroll_view.x + scroll_offset_x



class AnalyticsTab(Screen):

    primary_pink = ListProperty(PRIMARY_PINK)
    primary_blue = ListProperty(PRIMARY_BLUE)
    light_pink = ListProperty(LIGHT_PINK)
    light_blue = ListProperty(LIGHT_BLUE)
    error_red = ListProperty(ERROR_RED)
    success_green = ListProperty(SUCCESS_GREEN)
    white = ListProperty(WHITE)
    dark_text = ListProperty(DARK_TEXT)
    light_gray = ListProperty(LIGHT_GRAY)
    dark_gray = ListProperty(DARK_GRAY)
    warning_orange = ListProperty(WARNING_ORANGE) 

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'analytics'
        self.user_cards = []
        self.envelopes_data = []
        self.current_popup = None
        self.analytics_data = {}
        self.daily_expenses = []
        self.use_budget = False
        
        Clock.schedule_once(self.create_ui, 0.1)
    
    def get_app(self): return App.get_running_app()
    
    def create_ui(self, dt=None): self.load_data()
    
    def on_enter(self): Clock.schedule_once(lambda dt: self.load_data(), 0.1)
    
    def load_data(self):
        try:
            app = self.get_app()
            if not hasattr(app, 'current_user_id') or not app.current_user_id: return
            
            user_id = app.current_user_id
            self.user_cards = get_user_cards(cursor, user_id) 
            self.envelopes_data = get_user_envelopes(cursor, user_id)
            
            if not self.envelopes_data:
                self.create_default_envelopes()
            else:
                self.load_analytics_data(user_id)
                self.load_daily_expenses(user_id)
                self.update_envelopes_display()
                self.update_stats_display()
                self.update_charts_display()
            
        except Exception as e:
            print(f"Помилка завантаження даних аналітики: {traceback.format_exc()}")
    
    def create_default_envelopes(self):
        try:
            app = self.get_app()
            user_id = app.current_user_id
            default_envelopes = [
                {"name": "Їжа", "color": ENVELOPE_COLORS[0]}, {"name": "Транспорт", "color": ENVELOPE_COLORS[1]},
                {"name": "Розваги", "color": ENVELOPE_COLORS[2]}, {"name": "Одяг", "color": ENVELOPE_COLORS[3]},
                {"name": "Здоров'я", "color": ENVELOPE_COLORS[4]}, {"name": "Подарунки", "color": ENVELOPE_COLORS[5]}
            ]
            
            for i, envelope in enumerate(default_envelopes):
                create_envelope(cursor, conn, user_id, envelope["name"], get_unique_color(i), 0.0)
            
            self.envelopes_data = get_user_envelopes(cursor, user_id)
            self.load_analytics_data(user_id)
            self.load_daily_expenses(user_id)
            self.update_envelopes_display()
            self.update_stats_display()
            self.update_charts_display()
            
        except Exception as e:
            print(f"Помилка створення стандартних конвертів: {e}")
    
    def load_analytics_data(self, user_id):
        try:
            self.analytics_data = get_analytics_data(cursor, user_id, 'month')
            savings_data = self.get_savings_data(user_id) 
            
            if savings_data:
                self.analytics_data['total_savings'] = savings_data['total_savings']
                self.analytics_data['savings_progress'] = savings_data['savings_progress']
                self.analytics_data['active_savings_plans'] = savings_data['active_plans_count']

            envelopes_data_sorted = sorted(self.envelopes_data, key=lambda e: e['name'])

            self.envelopes_for_chart = []
            for envelope in envelopes_data_sorted:
                if envelope['current_amount'] > 0:
                    self.envelopes_for_chart.append({
                        'name': envelope['name'], 'amount': envelope['current_amount'], 'color': envelope['color']
                    })
            
            if savings_data and savings_data['total_savings'] > 0:
                self.envelopes_for_chart.append({'name': 'Заощадження', 'amount': savings_data['total_savings'], 'color': SAVINGS_PINK})
            
        except Exception as e:
            print(f"Помилка завантаження аналітики: {traceback.format_exc()}")
            self.analytics_data = {}
            self.envelopes_for_chart = []

    def load_daily_expenses(self, user_id):
        """Завантажує витрати за кожен день поточного місяця з envelope_transactions."""
        try:
            now = datetime.now()
            start_of_month = now.replace(day=1).strftime('%Y-%m-%d')
            
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            end_of_month = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT 
                    DATE(created_at), 
                    SUM(amount) 
                FROM envelope_transactions 
                WHERE user_id = ? 
                  AND DATE(created_at) BETWEEN ? AND ?
                GROUP BY 1 
                ORDER BY 1 ASC
            ''', (user_id, start_of_month, end_of_month))
            
            results = cursor.fetchall()
            
            self.daily_expenses = [{'date': date_str, 'amount': float(amount)} for date_str, amount in results if amount is not None and amount > 0]

        except Exception as e:
            print(f"Помилка завантаження щоденних витрат: {traceback.format_exc()}")
            self.daily_expenses = []

    def get_savings_data(self, user_id):
        try:
            cursor.execute('''
                SELECT SUM(current_amount) as total_savings, SUM(target_amount) as total_target, COUNT(*) as active_plans_count
                FROM savings_plans WHERE user_id=? AND status='active'
            ''', (user_id,))
            
            result = cursor.fetchone()
            total_savings = result[0] or 0
            total_target = result[1] or 0
            active_plans = result[2] or 0
            
            savings_progress = (total_savings / total_target * 100) if total_target > 0 else 0
            
            return {'total_savings': total_savings, 'total_target': total_target, 'savings_progress': savings_progress, 'active_plans_count': active_plans}
            
        except Exception as e:
            print(f"Помилка отримання даних заощаджень: {e}")
            return None
    
    def update_envelopes_display(self):
        if 'envelopes_container' not in self.ids: return
            
        container = self.ids.envelopes_container
        container.clear_widgets()
        container.cols = 3
        
        if not self.envelopes_data: return
        
        for envelope_data in self.envelopes_data:
            envelope_card = CompactEnvelopeCard(envelope_data, on_manage_callback=self.on_envelope_action)
            container.add_widget(envelope_card)
    
    def update_stats_display(self):
        if 'stats_container' not in self.ids: return
            
        container = self.ids.stats_container
        container.clear_widgets()
        container.cols = 2
        
        if not self.analytics_data:
            container.add_widget(Label(text="Немає даних для аналітики", font_size=dp(12), color=DARK_GRAY, size_hint_y=None, height=dp(50)))
            return
        
        stats_cards = [
            {'title': 'Доходи', 'value': f"${self.analytics_data.get('total_income', 0):.0f}", 'subtitle': 'За місяць', 'color': SUCCESS_GREEN},
            {'title': 'Витрати', 'value': f"${self.analytics_data.get('total_expenses', 0):.0f}", 'subtitle': 'За місяць', 'color': ERROR_RED},
            {'title': 'Заощадження', 'value': f"${self.analytics_data.get('total_savings', 0):.0f}", 'subtitle': f"{self.analytics_data.get('savings_progress', 0):.0f}% від цілі", 'color': SAVINGS_PINK},
            {'title': 'Транзакції', 'value': self.analytics_data.get('transactions_count', 0), 'subtitle': 'За місяць', 'color': WARNING_ORANGE}
        ]
        
        for stat in stats_cards:
            container.add_widget(StatCard(stat['title'], stat['value'], stat['subtitle'], stat['color']))
    
    def update_charts_display(self):
        """Відображає дві діаграми поруч."""
        if 'charts_container' not in self.ids: return
            
        container = self.ids.charts_container
        container.clear_widgets()
        
        charts_wrapper = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(300))
        
        # 1. Кругова діаграма (Розподіл коштів)
        pie_layout = BoxLayout(orientation='vertical', size_hint_x=0.5)
        pie_layout.add_widget(Label(text="Розподіл коштів", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(25)))
        
        if self.envelopes_for_chart:
            pie_chart = SimplePieChartWidget(self.envelopes_for_chart)
            pie_layout.add_widget(pie_chart)
        else:
            pie_layout.add_widget(Label(text="Немає даних", font_size=dp(12), color=DARK_GRAY))
            
        charts_wrapper.add_widget(pie_layout)


        # 2. Стовпчаста діаграма (Витрати за місяць)
        bar_layout = BoxLayout(orientation='vertical', size_hint_x=0.5)
        bar_layout.add_widget(Label(text="Витрати за місяць", font_size=dp(16), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(25)))
        
        if self.daily_expenses:
            bar_chart = SimpleBarChartWidget(self.daily_expenses)
            bar_layout.add_widget(bar_chart)
        else:
            bar_layout.add_widget(Label(text="Немає даних", font_size=dp(12), color=DARK_GRAY))
            
        charts_wrapper.add_widget(bar_layout)
        
        container.add_widget(charts_wrapper)

    def create_envelope(self):
        """ВИПРАВЛЕНО: Обробляє створення нового конверта (усунення AttributeError)."""
        try:
            name_input = self.ids.envelope_name_input
            budget_input = self.ids.envelope_budget_input
            message_label = self.ids.analytics_message
            
            name = name_input.text.strip()
            budget_text = budget_input.text.strip()
            
            if not name:
                message_label.text = "Введіть назву конверту"
                message_label.color = ERROR_RED
                return
            
            budget = float(budget_text) if budget_text else 0.0
            
            color = get_unique_color(len(self.envelopes_data))
            
            app = self.get_app()
            envelope_id = create_envelope(cursor, conn, app.current_user_id, name, color, budget)
            
            if envelope_id:
                message_label.text = f"Конверт '{name}' створено!"
                message_label.color = SUCCESS_GREEN
                name_input.text = ""
                budget_input.text = ""
                self.load_data() 
            else:
                message_label.text = "Помилка створення конверту"
                message_label.color = ERROR_RED
                
        except ValueError:
            self.ids.analytics_message.text = "Введіть коректну суму бюджету"
            self.ids.analytics_message.color = ERROR_RED
        except Exception as e:
            print(f"Помилка створення конверту: {e}")
            self.ids.analytics_message.text = "Сталася помилка"
            self.ids.analytics_message.color = ERROR_RED

    def on_envelope_action(self, envelope_data, action):
        if action == 'add': self.show_add_money_modal(envelope_data)
        elif action == 'edit': self.show_edit_envelope_modal(envelope_data)
    
    def show_edit_envelope_modal(self, envelope_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        title = Label(text=f"Редагування: {envelope_data['name']}", font_size=dp(18), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(35))
        content.add_widget(title)
        
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        name_layout.add_widget(Label(text='Назва:', size_hint_x=0.3, color=DARK_TEXT, font_size=dp(16)))
        name_input = WhiteTextInput(text=envelope_data['name'], size_hint_x=0.7)
        name_layout.add_widget(name_input); content.add_widget(name_layout)
        
        budget_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        budget_layout.add_widget(Label(text='Бюджет:', size_hint_x=0.3, color=DARK_TEXT, font_size=dp(16)))
        budget_input = WhiteTextInput(text=str(envelope_data['budget_limit']) if envelope_data['budget_limit'] > 0 else "", hint_text="Не обов'язково", input_filter='float', size_hint_x=0.7)
        budget_layout.add_widget(budget_input); content.add_widget(budget_layout)
        
        error_label = Label(text="", color=ERROR_RED, size_hint_y=None, height=dp(25))
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        
        delete_btn = WhiteButton(text="Видалити", background_color=ERROR_RED)
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT)
        save_btn = WhiteButton(text="Зберегти", background_color=SUCCESS_GREEN)
        
        def save_changes(instance):
            new_name = name_input.text.strip(); budget_text = budget_input.text.strip()
            if not new_name: error_label.text = "Введіть назву конверту"; return
            
            try:
                new_budget = float(budget_text) if budget_text else 0.0
                success = update_envelope(cursor, conn, envelope_data['id'], name=new_name, budget_limit=new_budget)
                
                if success:
                    popup.dismiss(); self.load_data(); self.show_success_message(f"Конверт '{new_name}' успішно оновлено!")
                else: error_label.text = "Помилка при оновленні конверту"
                    
            except ValueError: error_label.text = "Введіть коректну суму бюджету"
            except Exception as e: print(f"Error updating envelope: {traceback.format_exc()}"); error_label.text = "Сталася помилка"
        
        def delete_envelope(instance):
            confirm_content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
            
            confirm_content.add_widget(Label(text=f"Ви впевнені, що хочете видалити\nконверт '{envelope_data['name']}'?", halign='center', color=DARK_TEXT, font_size=dp(16)))
            confirm_buttons = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
            
            def confirm_delete(instance):
                try:
                    cursor.execute("DELETE FROM envelopes WHERE id=?", (envelope_data['id'],)); cursor.execute("DELETE FROM envelope_transactions WHERE envelope_id=?", (envelope_data['id'],)); conn.commit()
                    confirm_popup.dismiss(); popup.dismiss(); self.load_data(); self.show_success_message(f"Конверт '{envelope_data['name']}' успішно видалено!")
                except Exception as e: print(f"Помилка видалення конверту: {e}"); error_label.text = "Помилка при видаленні конверту"
            
            confirm_popup = WhitePopup(title='Підтвердження видалення', content=confirm_content, size_hint=(0.7, 0.3))
            
            confirm_buttons.add_widget(WhiteButton(text='Ні', background_color=LIGHT_GRAY, color=DARK_TEXT, on_press=lambda x: confirm_popup.dismiss()))
            confirm_buttons.add_widget(WhiteButton(text='Так', background_color=ERROR_RED, on_press=confirm_delete))
            confirm_content.add_widget(confirm_buttons)
            confirm_popup.open()
        
        delete_btn.bind(on_press=delete_envelope)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        save_btn.bind(on_press=save_changes)
        
        buttons_layout.add_widget(delete_btn); buttons_layout.add_widget(cancel_btn); buttons_layout.add_widget(save_btn)
        content.add_widget(buttons_layout)
        
        popup = WhitePopup(title='Редагування конверту', content=content, size_hint=(0.85, 0.5))
        self.current_popup = popup
        popup.open()
    
    def show_add_money_modal(self, envelope_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        title = Label(text=f"Поповнення: {envelope_data['name']}", font_size=dp(18), bold=True, color=DARK_TEXT, size_hint_y=None, height=dp(35))
        content.add_widget(title)
        
        card_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        card_layout.add_widget(Label(text="З картки:", size_hint_x=0.4, color=DARK_TEXT, font_size=dp(16)))
        
        if not self.user_cards:
            card_spinner = Spinner(text="Немає карток", values=["Немає карток"], size_hint_x=0.6, background_color=WHITE, color=DARK_TEXT)
        else:
            card_spinner = Spinner(text=self.user_cards[0]['name'], values=[card['name'] for card in self.user_cards], size_hint_x=0.6, background_color=WHITE, color=DARK_TEXT)
        
        card_layout.add_widget(card_spinner); content.add_widget(card_layout)
        
        amount_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        amount_layout.add_widget(Label(text="Сума:", size_hint_x=0.4, color=DARK_TEXT, font_size=dp(16)))
        amount_input = WhiteTextInput(hint_text="Сума поповнення", input_filter='float', size_hint_x=0.6)
        amount_layout.add_widget(amount_input); content.add_widget(amount_layout)
       
        desc_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        desc_layout.add_widget(Label(text="Опис:", size_hint_x=0.4, color=DARK_TEXT, font_size=dp(16)))
        desc_input = WhiteTextInput(hint_text="Не обов'язково", size_hint_x=0.6)
        desc_layout.add_widget(desc_input); content.add_widget(desc_layout)
        
        error_label = Label(text="", color=ERROR_RED, size_hint_y=None, height=dp(25))
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        
        cancel_btn = WhiteButton(text="Скасувати", background_color=LIGHT_GRAY, color=DARK_TEXT)
        add_btn = WhiteButton(text="Поповнити", background_color=SUCCESS_GREEN)
        
        def add_money(instance):
            amount_text = amount_input.text.strip(); description = desc_input.text.strip(); card_name = card_spinner.text
            
            if card_name == "Немає карток": error_label.text = "Немає доступних карток"; return
            if not amount_text: error_label.text = "Введіть суму"; return
            
            try:
                amount = float(amount_text);
                if amount <= 0: error_label.text = "Сума має бути додатною"; return
                
                card_id = next((card['id'] for card in self.user_cards if card['name'] == card_name), None)
                if not card_id: error_label.text = "Картку не знайдено"; return
                
                selected_card = next((card for card in self.user_cards if card['id'] == card_id), None)
                if selected_card and selected_card['balance'] < amount:
                    error_label.text = f"Недостатньо коштів. Доступно: {selected_card['balance']:.2f} $"; return
                
                success = self.add_money_to_envelope(envelope_data['id'], amount, description, card_id)
                if success: popup.dismiss(); self.load_data(); self.show_success_message(f"Конверт '{envelope_data['name']}' поповнено!")
                else: error_label.text = "Помилка при поповненні"
                    
            except ValueError: error_label.text = "Введіть коректну суму"
            except Exception as e: print(f"Помилка поповнення конверту: {e}"); error_label.text = "Сталася помилка"
        
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        add_btn.bind(on_press=add_money)
        
        buttons_layout.add_widget(cancel_btn); buttons_layout.add_widget(add_btn); content.add_widget(buttons_layout)
        
        popup = WhitePopup(title='Поповнення конверту', content=content, size_hint=(0.85, 0.5))
        self.current_popup = popup
        popup.open()
    
    def add_money_to_envelope(self, envelope_id, amount, description, card_id):
        """Додати гроші до конверту та оновити баланс картки."""
        try:
            app = self.get_app()
            
            # 1. Зняття з картки
            cursor.execute("UPDATE user_cards SET balance = balance - ? WHERE id = ?", (amount, card_id))
            
            # 2. Додавання в конверт
            success = add_to_envelope(cursor, conn, app.current_user_id, envelope_id, amount, description, card_id)
            
            conn.commit()
            
            return success
        except Exception as e:
            print(f"Помилка поповнення конверту: {e}")
            return False
    
    def show_success_message(self, message):
        """Показати повідомлення про успіх (білий дизайн)"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        content.add_widget(Label(text=message, color=SUCCESS_GREEN, font_size=dp(16)))
        content.add_widget(WhiteButton(text='OK', background_color=PRIMARY_BLUE, on_press=lambda x: popup.dismiss()))
        
        popup = WhitePopup(title='Успіх', content=content, size_hint=(0.6, 0.3))
        self.current_popup = popup
        popup.open()

    def show_error_message(self, message):
        """Показати повідомлення про помилку (білий дизайн)"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        content.add_widget(Label(text=message, color=ERROR_RED, font_size=dp(16)))
        content.add_widget(WhiteButton(text='OK', background_color=PRIMARY_BLUE, on_press=lambda x: popup.dismiss()))
        
        popup = WhitePopup(title='Помилка', content=content, size_hint=(0.6, 0.3))
        self.current_popup = popup
        popup.open()        