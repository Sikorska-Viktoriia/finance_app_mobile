from datetime import datetime, timedelta
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.properties import NumericProperty, StringProperty, ListProperty, ObjectProperty 
import traceback
from typing import Optional, Dict, Any, List

# --- Імпорт з utils ---
try:
    from utils.db_manager import cursor, conn, log_transaction, log_savings_transaction, get_user_cards, get_user_card_by_id
    from utils.widgets import SavingsPlanItem
except ImportError:
    # --- ЗАГЛУШКИ ДЛЯ ТЕСТУВАННЯ (MOCK) ---
    class MockCursor:
        def execute(self, *args, **kwargs): pass
        def fetchall(self): 
            return [
                (1, 'Відпустка на морі', 5000.0, 1500.0, '2026-07-01', 'active'),
                (2, 'Новий ноутбук', 2000.0, 2000.0, '2025-12-31', 'completed')
            ]
        def fetchone(self): return (1500.0,) 
        @property
        def lastrowid(self): return 1
    cursor = MockCursor()
    class MockConn:
        def commit(self): pass
    conn = MockConn()
    def log_transaction(*args): print(f"[MOCK] Log transaction: {args}")
    def log_savings_transaction(*args): print(f"[MOCK] Log savings transaction: {args}")
    def get_user_cards(cursor, user_id): 
        return [{'id': 1, 'name': 'Demo Card', 'balance': 1000.0}, {'id': 2, 'name': 'Bank Card', 'balance': 500.0}]
    def get_user_card_by_id(cursor, card_id): 
        if card_id == 1: return {'id': 1, 'name': 'Demo Card', 'balance': 1000.0}
        return None

    # --- ФІНАЛЬНА МАКСИМАЛЬНО ОПТИМІЗОВАНА ЗАГЛУШКА SavingsPlanItem ---
    from kivy.uix.behaviors import ButtonBehavior
    class SavingsPlanItem(ButtonBehavior, BoxLayout):
        __events__ = ('on_release',) 
        def __init__(self, plan_name, current_amount, target_amount, progress, days_left, status, plan_id, is_selected, **kwargs):
            kwargs.setdefault('size_hint_y', None)
            kwargs.setdefault('height', dp(75)) 
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = dp(8) 
            self.plan_id = plan_id
            self.is_selected = is_selected
            self.spacing = dp(2) 
            
            bg_color = LIGHT_BLUE if is_selected else LIGHT_GRAY
            
            with self.canvas.before:
                Color(*bg_color)
                self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            
            self.bind(pos=self.update_graphics, size=self.update_graphics)
            
            # --- РЯДОК 1: НАЗВА ТА ЦІЛЬОВА СУМА (Стиснено) ---
            header_layout = BoxLayout(size_hint_y=None, height=dp(20)) 
            
            display_name = plan_name if len(plan_name) < 20 else plan_name[:17] + "..."
            
            # 1. Назва + Ціль (Об'єднано для економії місця)
            header_layout.add_widget(Label(
                text=f"{display_name} (Ціль: ${target_amount:.0f})", color=DARK_TEXT, font_size=dp(12), 
                size_hint_x=0.7, halign='left', valign='middle'
            ))
            
            # 2. Статус (Праворуч)
            header_layout.add_widget(Label(
                text=f"[{status.upper()}]", color=PRIMARY_PINK, font_size=dp(10), 
                size_hint_x=0.3, halign='right', valign='middle'
            ))
            
            self.add_widget(header_layout)

            # --- РЯДОК 2: ПОТОЧНИЙ БАЛАНС, ПРОГРЕС ТА ДНІ (Критична інформація) ---
            progress_row = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(5))
            
            # A. Поточний баланс (Залишок місця) - це критична інформація
            progress_row.add_widget(Label(
                text=f"Зібрано: ${current_amount:.0f}", color=DARK_TEXT, font_size=dp(12), 
                size_hint_x=1, halign='left', valign='middle'
            ))
            
            # B. Прогрес (%) та Дні (ФІКСОВАНА ШИРИНА)
            progress_row.add_widget(Label(
                text=f"{progress:.0f}% / {days_left} дн.", color=ERROR_RED, font_size=dp(12), 
                size_hint_x=None, width=dp(90), halign='right', valign='middle'
            ))

            self.add_widget(progress_row)
            
            self.add_widget(Label(text="", size_hint_y=None, height=dp(5)))
            
        def update_graphics(self, *args):
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
        
        def on_release(self): 
            pass


# --- КОНСТАНТИ КОЛЬОРУ ---
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


# --- 1. ДОПОМІЖНІ ВІДЖЕТИ ---

class WhitePopup(Popup):
    """Кастомний Popup, який використовує затемнення, але не має стандартного фону."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.background_color = [0, 0, 0, 0.1] 
        self.background = '' 
        self.separator_height = 0
        self.auto_dismiss = False

class WhiteButton(Button):
    """Кастомна кнопка з динамічним фоном."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = kwargs.get('background_color', PRIMARY_BLUE)
        self.color = kwargs.get('color', WHITE) 
        self.font_size = kwargs.get('font_size', dp(16))
        self.size_hint_y = None
        self.height = kwargs.get('height', dp(45))
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
    """Кастомне поле введення з рамкою."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.padding = [dp(10), dp(10)] 
        self.background_normal = ''
        self.background_active = ''
        self.background_color = WHITE
        self.foreground_color = DARK_TEXT
        self.font_size = kwargs.get('font_size', dp(16)) 
        self.size_hint_y = None
        self.height = kwargs.get('height', dp(40)) 
        self.cursor_color = PRIMARY_BLUE
        self.hint_text_color = LIGHT_GRAY
        self.write_tab = False
        
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=1)
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)


class DatePickerPopup(WhitePopup):
    """Попап для вибору дати."""
    def __init__(self, callback, initial_date: Optional[datetime.date] = None, **kwargs):
        self.callback = callback
        self.selected_date = initial_date or datetime.now().date()
        super().__init__(**kwargs)
        self.size_hint = (0.9, 0.7) 
        self.create_widgets()
    
    def create_widgets(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15)) 
        
        with content.canvas.before:
            Color(*WHITE); Rectangle(pos=content.pos, size=content.size)
            Color(*DARK_GRAY); Line(rectangle=(content.x, content.y, content.width, content.height), width=1.2)
        
        self.date_label = Label(text=self.selected_date.strftime('%d.%m.%Y'), font_size=dp(20), size_hint_y=None, height=dp(40), color=DARK_TEXT, bold=True) 
        content.add_widget(self.date_label)
        
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8)) 
        
        nav_layout.add_widget(WhiteButton(text='<', background_color=LIGHT_GRAY, color=DARK_TEXT, on_press=self.prev_day, height=dp(40), font_size=dp(14)))
        nav_layout.add_widget(WhiteButton(text='СЬОГОДНІ', background_color=PRIMARY_PINK, color=WHITE, on_press=self.set_today, height=dp(40), font_size=dp(14)))
        nav_layout.add_widget(WhiteButton(text='>', background_color=LIGHT_GRAY, color=DARK_TEXT, on_press=self.next_day, height=dp(40), font_size=dp(14)))
        content.add_widget(nav_layout)
        
        quick_layout = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(90))
        quick_buttons = [
            ('+7 днів', PRIMARY_BLUE, 7), ('+30 днів', PRIMARY_BLUE, 30), ('+90 днів', PRIMARY_BLUE, 90),
            ('+1 місяць', PRIMARY_PINK, 30), ('+3 місяці', PRIMARY_PINK, 90), ('+6 місяців', PRIMARY_PINK, 180),
        ]
        for text, color, days in quick_buttons:
            btn = WhiteButton(text=text, background_color=color, color=WHITE, height=dp(40), font_size=dp(12)) 
            btn.bind(on_press=lambda instance, d=days: self.add_days(d))
            quick_layout.add_widget(btn)
        content.add_widget(quick_layout)
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(40)) 
        btn_layout.add_widget(WhiteButton(text='ОБРАТИ ДАТУ', background_color=PRIMARY_PINK, color=WHITE, on_press=self.select_date, height=dp(40), font_size=dp(14)))
        btn_layout.add_widget(WhiteButton(text='СКАСУВАТИ', background_color=LIGHT_GRAY, color=DARK_TEXT, on_press=lambda x: self.dismiss(), height=dp(40), font_size=dp(14)))
        content.add_widget(btn_layout)
        
        self.content = content
    
    def prev_day(self, instance): self.selected_date -= timedelta(days=1); self.update_display()
    def next_day(self, instance): self.selected_date += timedelta(days=1); self.update_display()
    def set_today(self, instance): self.selected_date = datetime.now().date(); self.update_display()
    def add_days(self, days): self.selected_date += timedelta(days=days); self.update_display()
    
    def update_display(self):
        self.date_label.text = self.selected_date.strftime('%d.%m.%Y')
    
    def select_date(self, instance):
        self.callback(self.selected_date.strftime('%Y-%m-%d'))
        self.dismiss()


# --- 2. ГОЛОВНИЙ КЛАС ЕКРАНА (SavingsTab) ---

class SavingsTab(Screen):
    selected_plan_id = NumericProperty(0, allownone=True) 
    selected_plan_name = StringProperty("")
    user_cards = ListProperty([])

    def get_app(self) -> App:
        return App.get_running_app()

    # --- ЖИТТЄВИЙ ЦИКЛ ---

    def on_enter(self):
        Clock.schedule_once(self._deferred_update, 0.1)
    
    def _deferred_update(self, dt):
        self.load_user_cards()
        self.clear_inputs()
        self.update_savings_tab()

    def load_user_cards(self):
        """Завантажує актуальний список карток користувача в user_cards ListProperty."""
        app = self.get_app()
        user_id = getattr(app, 'current_user_id', 1) 
        
        if user_id:
            try:
                self.user_cards = get_user_cards(cursor, user_id)
            except Exception:
                self.user_cards = []
        else:
            self.user_cards = []
    
    def clear_inputs(self):
        """Очищення полів вводу та скидання вибраного плану."""
        if 'plan_name_input' in self.ids: self.ids.plan_name_input.text = ""
        if 'target_amount_input' in self.ids: self.ids.target_amount_input.text = ""
        if 'deadline_input' in self.ids: self.ids.deadline_input.text = ""
        if 'savings_message' in self.ids: self.ids.savings_message.text = ""
        
        self.selected_plan_id = None
        self.selected_plan_name = ""

    # --- УТИЛІТИ ---

    def _display_message(self, message: str, is_error: bool = False):
        """Централізоване відображення повідомлень."""
        if 'savings_message' in self.ids:
            self.ids.savings_message.text = message
            self.ids.savings_message.color = ERROR_RED if is_error else SUCCESS_GREEN

    def _validate_amount(self, amount_text: str) -> Optional[float]:
        """Валідує суму вводу."""
        try:
            amount = float(amount_text)
            if amount <= 0:
                self._display_message("Сума має бути додатною", True)
                return None
            return amount
        except ValueError:
            self._display_message("Введіть коректну суму", True)
            return None

    def _update_home_tab(self):
        """Викликає оновлення історії транзакцій на HomeTab."""
        try:
            root_sm = self.get_app().root.get_screen('dashboard_screen').ids.tab_manager
            root_sm.get_screen('home_tab').update_transactions_history()
        except Exception:
            print("Попередження: Не вдалося оновити HomeTab.")

    # --- ДИНАМІЧНЕ ОНОВЛЕННЯ GUI ---

    def update_savings_tab(self):
        """Динамічно завантажує та відображає плани заощаджень."""
        if 'savings_container' not in self.ids: return
        savings_container = self.ids.savings_container
        savings_container.clear_widgets()
        
        try:
            app = self.get_app()
            # ВИПРАВЛЕННЯ: Використовуємо 1 як резервний ID, якщо справжній ID не встановлено
            user_id = getattr(app, 'current_user_id', 1) 

            if not user_id:
                savings_container.add_widget(Label(text="Будь ласка, увійдіть в систему (ID: None)", font_size=dp(16), color=DARK_TEXT))
                return
            
            cursor.execute(
                "SELECT id, name, target_amount, current_amount, deadline, status FROM savings_plans WHERE user_id=? ORDER BY created_at DESC",
                (user_id,)
            )
            plans = cursor.fetchall()
            
            print(f"[DEBUG] User ID: {user_id}. Plans Fetched: {len(plans) if plans else 0}") 

            if not plans:
                savings_container.add_widget(Label(
                    text="Створіть свій перший план заощаджень!", font_size=dp(18), color=DARK_TEXT, halign="center", text_size=(dp(300), None)
                ))
                return
            
            # --- РЕНДЕРИНГ КОЖНОГО ПЛАНУ ---
            for plan in plans:
                
                if len(plan) != 6:
                    print(f"[ERROR] Skipping invalid plan data (wrong length): {plan}")
                    continue
                
                plan_id, name, target, current, deadline, status = plan
                
                target_float = float(target) if target is not None else 0
                current_float = float(current) if current is not None else 0
                
                progress = (current_float / target_float * 100) if target_float > 0 else 0
                days_left = 0
                
                if deadline:
                    try:
                        if deadline.strip():
                            deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                            today = datetime.now().date()
                            days_left = max(0, (deadline_date - today).days)
                    except ValueError:
                        print(f"[ERROR] Invalid date format for plan ID {plan_id}: {deadline}")
                        days_left = -1 
                
                is_completed = current_float >= target_float
                
                print(f"[DEBUG] Rendering Plan ID {plan_id}: {name} (Progress: {progress:.1f}%)") 
                
                plan_container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(140))
                
                # 1. Елемент плану (SavingsPlanItem)
                try:
                    plan_item = SavingsPlanItem(
                        plan_name=name, current_amount=current_float, target_amount=target_float,
                        progress=progress, days_left=days_left, status=status, plan_id=plan_id,
                        is_selected=(self.selected_plan_id == plan_id)
                    )
                    plan_item.bind(on_release=lambda instance, p_id=plan_id, p_name=name: self.on_plan_select(p_id, p_name))
                    plan_container.add_widget(plan_item)
                except Exception as e:
                    print(f"[CRITICAL] Failed to render SavingsPlanItem for ID {plan_id}: {traceback.format_exc()}")
                    savings_container.add_widget(Label(text=f"Помилка віджету: {name}", color=ERROR_RED, size_hint_y=None, height=dp(30)))
                    continue 
                
                # 2. Панель операцій (весь код, що слідує, не змінений)
                
                operations_layout = BoxLayout(
                    orientation='horizontal', size_hint_y=None, height=dp(40), 
                    spacing=dp(5), padding=[dp(5), dp(5), dp(5), dp(5)] 
                )
                
                amount_input = WhiteTextInput(hint_text='Сума', input_filter='float', size_hint_x=0.3, font_size=dp(12), height=dp(35))
                operations_layout.add_widget(amount_input)
                
                def bind_op_button(text, color, op_type, pid, pname, inp):
                    btn_size = 0.17 
                    btn_font_size = dp(11) 
                    btn_height = dp(35)
                    
                    if op_type in ["add", "remove"]: 
                        btn_size = 0.17
                    elif op_type == "delete":
                        btn_size = 0.12 
                        btn_font_size = dp(14) 
                    elif op_type in ["complete", "edit"]:
                        btn_size = 0.2
                    
                    btn = Button(
                        text=text, 
                        size_hint_x=btn_size, 
                        background_color=color, 
                        color=WHITE, 
                        font_size=btn_font_size, 
                        background_normal='',
                        height=btn_height 
                    )
                    
                    if op_type == "add": btn.bind(on_press=lambda x: self.add_to_plan(pid, pname, inp.text))
                    elif op_type == "remove": btn.bind(on_press=lambda x: self.remove_from_plan(pid, pname, inp.text))
                    elif op_type == "complete": btn.bind(on_press=lambda x: self.complete_savings_plan(pid, pname))
                    elif op_type == "edit": btn.bind(on_press=lambda x: self.edit_specific_plan(pid, pname))
                    elif op_type == "delete": 
                        btn.bold = True
                        btn.bind(on_press=lambda x: self.delete_specific_plan(pid, pname))
                        
                    return btn
                
                operations_layout.add_widget(bind_op_button('Додати', PRIMARY_PINK, "add", plan_id, name, amount_input))
                operations_layout.add_widget(bind_op_button('Вилучити', PRIMARY_BLUE, "remove", plan_id, name, amount_input))
                
                if is_completed:
                    operations_layout.add_widget(bind_op_button('Заверш.', SUCCESS_GREEN, "complete", plan_id, name, amount_input))
                else:
                    operations_layout.add_widget(bind_op_button('Редаг.', SUCCESS_GREEN, "edit", plan_id, name, amount_input))
                
                operations_layout.add_widget(bind_op_button('×', ERROR_RED, "delete", plan_id, name, amount_input))
                
                plan_container.add_widget(operations_layout)
                savings_container.add_widget(plan_container)
                
        except Exception as e:
            print(f"[CRITICAL] Error loading savings plans: {traceback.format_exc()}")
            savings_container.add_widget(Label(text=f"Критична помилка завантаження: {str(e)}", font_size=dp(16), color=ERROR_RED))
    
    # --- ДІЇ З ПЛАНАМИ ---

    def show_calendar(self):
        """Відображає попап вибору дати. (Викликається з KV)"""
        def set_date(date_str):
            self.ids.deadline_input.text = date_str
        
        popup = DatePickerPopup(
            callback=set_date,
            title='Оберіть дату дедлайну',
            size_hint=(0.9, 0.7) 
        )
        popup.open()

    def on_plan_select(self, plan_id, plan_name):
        """Оновлює стан виділеного плану та оновлює вкладку."""
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.update_savings_tab()
        
        if 'savings_message' in self.ids:
            self.ids.savings_message.text = f"Обрано план: {plan_name}"
            self.ids.savings_message.color = SUCCESS_GREEN

    def create_savings_plan(self):
        """Створює новий план заощаджень."""
        if not hasattr(self, 'ids'): return
        plan_name = self.ids.plan_name_input.text.strip()
        target_text = self.ids.target_amount_input.text.strip()
        deadline = self.ids.deadline_input.text.strip()
        
        if not plan_name: self._display_message("Введіть назву плану", True); return
        target_amount = self._validate_amount(target_text)
        if target_amount is None: return
        
        if deadline:
            try: datetime.strptime(deadline, '%Y-%m-%d')
            except ValueError: self._display_message("Невірний формат дати. Використовуйте РРРР-ММ-ДД", True); return
        
        try:
            app = self.get_app()
            user_id = getattr(app, 'current_user_id', 1) 
            cursor.execute("INSERT INTO savings_plans (user_id, name, target_amount, deadline) VALUES (?, ?, ?, ?)",
                (user_id, plan_name, target_amount, deadline if deadline else None))
            plan_id = cursor.lastrowid
            
            log_savings_transaction(cursor, conn, user_id, plan_id, 0, "plan_created", f"Створено план заощаджень: {plan_name}")
            conn.commit()
            
            self.clear_inputs()
            self.update_savings_tab()
            self._display_message(f"План '{plan_name}' успішно створено!")
            
        except Exception as e:
            print(f"Error creating plan: {traceback.format_exc()}")
            self._display_message(f"Помилка створення плану: {str(e)}", True)


    def add_to_plan(self, plan_id: int, plan_name: str, amount_text: str, card_id: Optional[int] = None):
        """Додає кошти до плану."""
        amount = self._validate_amount(amount_text)
        if amount is None: return

        if not card_id:
            self._show_card_selection_popup(plan_id, plan_name, amount, "add")
            return
        
        try:
            app = self.get_app()
            user_id = getattr(app, 'current_user_id', 1) 
            selected_card = get_user_card_by_id(cursor, card_id)
            if not selected_card: self._display_message("Картку не знайдено", True); return
            if amount > selected_card['balance']: self._display_message(f"Недостатньо коштів на картці. Доступно: ${selected_card['balance']:.2f}", True); return
            
            cursor.execute("SELECT current_amount, target_amount FROM savings_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
            plan = cursor.fetchone()
            current_amount, target_amount = plan
            
            if current_amount + amount > target_amount:
                max_amount = target_amount - current_amount
                self._display_message(f"Максимум: ${max_amount:.2f}", True); return
            
            cursor.execute("UPDATE user_cards SET balance = balance - ? WHERE id = ?", (amount, card_id))
            cursor.execute("UPDATE savings_plans SET current_amount = current_amount + ? WHERE id = ?", (amount, plan_id))
            
            log_transaction(cursor, conn, user_id, "savings_deposit", amount, f"Переведено до плану '{plan_name}' з картки {selected_card['name']}")
            log_savings_transaction(cursor, conn, user_id, plan_id, amount, "deposit", f"Додано до плану заощаджень з картки {selected_card['name']}")
            
            conn.commit()
            self.update_savings_tab()
            self._display_message(f"Успішно додано ${amount:.2f} до {plan_name} з картки {selected_card['name']}")
            self._update_home_tab()
        except Exception as e:
            print(f"Error adding to plan: {traceback.format_exc()}")
            self._display_message(f"Помилка додавання: {str(e)}", True)


    def remove_from_plan(self, plan_id: int, plan_name: str, amount_text: str, card_id: Optional[int] = None):
        """Вилучає кошти з плану."""
        amount = self._validate_amount(amount_text)
        if amount is None: return
        
        if not card_id:
            self._show_card_selection_popup(plan_id, plan_name, amount, "remove")
            return
            
        try:
            app = self.get_app()
            user_id = getattr(app, 'current_user_id', 1) 
            cursor.execute("SELECT current_amount FROM savings_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
            plan = cursor.fetchone()
            current_amount = plan[0] if plan else 0
            
            if amount > current_amount: self._display_message(f"Недостатньо коштів. Доступно: ${current_amount:.2f}", True); return
            
            selected_card = get_user_card_by_id(cursor, card_id)
            card_name = selected_card['name'] if selected_card else "картки"
            
            cursor.execute("UPDATE user_cards SET balance = balance + ? WHERE id = ?", (amount, card_id))
            cursor.execute("UPDATE savings_plans SET current_amount = current_amount - ? WHERE id = ?", (amount, plan_id))
            
            log_transaction(cursor, conn, user_id, "savings_return", amount, f"Повернено з плану '{plan_name}' на картку {card_name}")
            log_savings_transaction(cursor, conn, user_id, plan_id, amount, "withdrawal", f"Вилучено з плану заощаджень на картку {card_name}")
            
            conn.commit()
            self.update_savings_tab()
            self._display_message(f"Успішно вилучено ${amount:.2f} з {plan_name} на картку {card_name}")
            self._update_home_tab()
        except Exception as e:
            print(f"Error removing from plan: {traceback.format_exc()}")
            self._display_message(f"Помилка вилучення: {str(e)}", True)

    def complete_savings_plan(self, plan_id: int, plan_name: str):
        """Ініціює завершення плану та переказ коштів на картку."""
        try:
            app = self.get_app()
            user_id = getattr(app, 'current_user_id', 1) 
            cursor.execute("SELECT current_amount FROM savings_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
            plan = cursor.fetchone()
            current_amount = plan[0] if plan else 0
            
            if current_amount <= 0: self._display_message("У плані немає коштів для завершення", True); return
            
            self._show_card_selection_for_completion(plan_id, plan_name, current_amount)
            
        except Exception as e:
            print(f"Error in complete_savings_plan: {traceback.format_exc()}")
            self._display_message(f"Помилка завершення: {str(e)}", True)

    # --- РЕДАГУВАННЯ / ВИДАЛЕННЯ ---
    
    def edit_specific_plan(self, plan_id, plan_name):
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.edit_savings_plan()

    def delete_specific_plan(self, plan_id, plan_name):
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.delete_savings_plan()

    def edit_savings_plan(self):
        """Відображає попап для редагування вибраного плану."""
        if not self.selected_plan_id: self._display_message("Оберіть план", True); return
        
        # --- ФУНКЦІОНАЛ EDIT_SAVINGS_PLAN ---
        # АДАПТИВНІСТЬ: Зменшено spacing і padding
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(20))
        
        with content.canvas.before:
            Color(*WHITE); Rectangle(pos=content.pos, size=content.size)
            Color(*DARK_GRAY); Line(rectangle=(content.x, content.y, content.width, content.height), width=1.2)
       
        cursor.execute("SELECT name, target_amount, deadline FROM savings_plans WHERE id = ?", (self.selected_plan_id,))
        plan_data = cursor.fetchone()
        
        if not plan_data: return
        
        current_name, current_target, current_deadline = plan_data
        
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        name_layout.add_widget(Label(text='Назва:', size_hint_x=0.4, color=DARK_TEXT, font_size=dp(14), halign='left'))
        name_input = WhiteTextInput(text=current_name, size_hint_x=0.6, height=dp(40), font_size=dp(14))
        name_layout.add_widget(name_input)
        content.add_widget(name_layout)
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        target_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        target_layout.add_widget(Label(text='Цільова сума:', size_hint_x=0.4, color=DARK_TEXT, font_size=dp(14), halign='left'))
        target_input = WhiteTextInput(text=str(current_target), size_hint_x=0.6, height=dp(40), font_size=dp(14))
        target_layout.add_widget(target_input)
        content.add_widget(target_layout)
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        deadline_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        deadline_layout.add_widget(Label(text='Дедлайн:', size_hint_x=0.4, color=DARK_TEXT, font_size=dp(14), halign='left'))
        
        deadline_input = WhiteTextInput(text=current_deadline if current_deadline else "", hint_text="РРРР-ММ-ДД", size_hint_x=0.4, height=dp(40), font_size=dp(14))
        deadline_layout.add_widget(deadline_input)
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        calendar_btn = WhiteButton(text='/', background_color=PRIMARY_BLUE, size_hint_x=0.2, height=dp(40), font_size=dp(14))
        
        def show_calendar_popup(_):
            def set_date(date_str): deadline_input.text = date_str
            popup = DatePickerPopup(callback=set_date, title='Оберіть дату дедлайну', size_hint=(0.9, 0.7))
            popup.open()
            
        calendar_btn.bind(on_press=show_calendar_popup)
        deadline_layout.add_widget(calendar_btn)
        
        content.add_widget(deadline_layout)
        

        # АДАПТИВНІСТЬ: Зменшено spacing і height
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(40))
        
        def save_plan(_):
            try:
                new_name = name_input.text.strip()
                new_target = float(target_input.text.strip())
                new_deadline = deadline_input.text.strip()
                
                if not new_name:
                    self._display_message("Введіть назву плану", True); return
                
                if new_target <= 0:
                    self._display_message("Цільова сума має бути додатною", True); return
                
                if new_deadline:
                    try: datetime.strptime(new_deadline, '%Y-%m-%d')
                    except ValueError: self._display_message("Невірний формат дати", True); return
                
                app = self.get_app()
                user_id = getattr(app, 'current_user_id', 1) 
                
                cursor.execute(
                    "UPDATE savings_plans SET name=?, target_amount=?, deadline=? WHERE id=?",
                    (new_name, new_target, new_deadline if new_deadline else None, self.selected_plan_id)
                )
                
                log_savings_transaction(cursor, conn, user_id, self.selected_plan_id, 0, "plan_updated", f"Оновлено план заощаджень")
                
                conn.commit()
                
                self.selected_plan_name = new_name
                popup.dismiss()
                self.update_savings_tab()
                self._display_message("План успішно оновлено!")
                
            except ValueError:
                self._display_message("Введіть коректну цільову суму", True)
            except Exception as e:
                print(f"Error updating plan: {traceback.format_exc()}")
                self._display_message(f"Помилка оновлення: {str(e)}", True)
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        save_btn = WhiteButton(text='ЗБЕРЕГТИ', background_color=PRIMARY_PINK, on_press=save_plan, height=dp(40), font_size=dp(14))
        cancel_btn = WhiteButton(text='СКАСУВАТИ', background_color=LIGHT_GRAY, color=DARK_TEXT, on_press=lambda x: popup.dismiss(), height=dp(40), font_size=dp(14))
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)
        
        # АДАПТИВНІСТЬ: Зменшено size_hint
        popup = WhitePopup(title='Редагування плану заощаджень', content=content, size_hint=(0.9, 0.55)) 
        popup.open()
        # --- КІНЕЦЬ ФУНКЦІОНАЛУ EDIT_SAVINGS_PLAN ---

    def delete_savings_plan(self):
        """Ініціює видалення плану з поверненням коштів або без."""
        if not self.selected_plan_id: self._display_message("Оберіть план", True); return
        
        cursor.execute("SELECT current_amount FROM savings_plans WHERE id = ?", (self.selected_plan_id,))
        result = cursor.fetchone()
        current_amount = result[0] if result else 0

        if current_amount > 0:
            self._show_card_selection_for_deletion(self.selected_plan_id, self.selected_plan_name, current_amount)
        else:
            try:
                app = self.get_app()
                user_id = getattr(app, 'current_user_id', 1) 
                cursor.execute("DELETE FROM savings_plans WHERE id=?", (self.selected_plan_id,))
                log_savings_transaction(cursor, conn, user_id, self.selected_plan_id, 0, "plan_deleted", f"Видалено план заощаджень")
                conn.commit()
                
                self.clear_inputs()
                self.update_savings_tab()
                self._display_message("План успішно видалено!")
            except Exception as e:
                self._display_message(f"Помилка видалення: {str(e)}", True)
    
    # --- МЕТОДИ POPUP ДЛЯ ВИБОРУ КАРТКИ ---

    def _create_popup_content(self, title: str, info_text: str, button_text: str, callback_func, is_destructive: bool = False):
        """Універсальна фабрика для вмісту попапів вибору картки."""
        if not self.user_cards: self._display_message("У вас немає карток", True); return None
        
        # АДАПТИВНІСТЬ: Зменшено spacing і padding
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        # Малювання фону контенту Popup
        with content.canvas.before: Color(*WHITE); Rectangle(pos=content.pos, size=content.size); Color(*DARK_GRAY); Line(rectangle=(content.x, content.y, content.width, content.height), width=1.2)
        
        # АДАПТИВНІСТЬ: Зменшено font_size і height
        content.add_widget(Label(text=title, font_size=dp(16), color=DARK_TEXT, size_hint_y=None, height=dp(30), bold=True))
        content.add_widget(Label(text=info_text, font_size=dp(14), color=DARK_TEXT, size_hint_y=None, height=dp(40)))
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        card_spinner = Spinner(text=self.user_cards[0]['name'], values=[card['name'] for card in self.user_cards], size_hint_y=None, height=dp(40), background_color=WHITE, color=DARK_TEXT, font_size=dp(14))
        content.add_widget(card_spinner)
        
        # АДАПТИВНІСТЬ: Зменшено spacing і height
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(40))
        
        def confirm_action(_):
            selected_card = next((card for card in self.user_cards if card['name'] == card_spinner.text), None)
            if selected_card:
                callback_func(selected_card)
                popup.dismiss()
            
        confirm_color = ERROR_RED if is_destructive else PRIMARY_PINK
        
        # АДАПТИВНІСТЬ: Зменшено height і font_size
        btn_layout.add_widget(WhiteButton(text=button_text, background_color=confirm_color, on_press=confirm_action, height=dp(40), font_size=dp(14)))
        btn_layout.add_widget(WhiteButton(text='СКАСУВАТИ', background_color=LIGHT_GRAY, color=DARK_TEXT, on_press=lambda x: popup.dismiss(), height=dp(40), font_size=dp(14)))
        content.add_widget(btn_layout)
        
        # АДАПТИВНІСТЬ: Зменшено size_hint
        popup = WhitePopup(title='Вибір картки', content=content, size_hint=(0.85, 0.4))
        return popup, card_spinner
        
    def _show_card_selection_popup(self, plan_id: int, plan_name: str, amount: float, operation_type: str):
        """Відображає попап для операцій додавання/вилучення."""
        operation_text = "додавання до" if operation_type == "add" else "вилучення з"
        
        def callback(selected_card):
            card_id = selected_card['id']
            if operation_type == "add":
                self.add_to_plan(plan_id, plan_name, str(amount), card_id)
            else:
                self.remove_from_plan(plan_id, plan_name, str(amount), card_id)

        popup, _ = self._create_popup_content(
            title=f"Оберіть картку для {operation_text} плану",
            info_text=f"План: {plan_name}\nСума: ${amount:.2f}",
            button_text='ПІДТВЕРДИТИ',
            callback_func=callback
        )
        if popup: popup.open()

    def _show_card_selection_for_completion(self, plan_id: int, plan_name: str, amount: float):
        """Відображає попап для отримання коштів при завершенні плану."""
        def callback(selected_card):
            # Фінальна транзакція завершення
            try:
                app = self.get_app()
                user_id = getattr(app, 'current_user_id', 1)
                card_id = selected_card['id']
                
                cursor.execute("UPDATE user_cards SET balance = balance + ? WHERE id = ?", (amount, card_id))
                cursor.execute("UPDATE savings_plans SET status='completed', current_amount=0 WHERE id=?", (plan_id,))
                
                log_transaction(cursor, conn, user_id, "savings_completed", amount, f"Завершено план: {plan_name} на картку {selected_card['name']}")
                log_savings_transaction(cursor, conn, user_id, plan_id, amount, "plan_completed", f"Завершено план на картку {selected_card['name']}")
                
                conn.commit()
                self.update_savings_tab()
                self._display_message(f"План '{plan_name}' успішно завершено! ${amount:.2f} додано на картку {selected_card['name']}.")
                self._update_home_tab()
                # popup.dismiss() - закривається в _create_popup_content
            except Exception as e:
                self._display_message(f"Помилка завершення плану: {str(e)}", True)
        
        popup, _ = self._create_popup_content(
            title=f"Оберіть картку для отримання коштів",
            info_text=f"План: {plan_name}\nСума: ${amount:.2f}",
            button_text='ЗАВЕРШИТИ',
            callback_func=callback,
            is_destructive=False
        )
        if popup: popup.open()
        
    def _show_card_selection_for_deletion(self, plan_id: int, plan_name: str, amount: float):
        """Відображає попап для повернення коштів при видаленні плану."""
        def callback(selected_card):
            # Фінальна транзакція видалення
            try:
                app = self.get_app()
                user_id = getattr(app, 'current_user_id', 1)
                card_id = selected_card['id']
                
                cursor.execute("UPDATE user_cards SET balance = balance + ? WHERE id = ?", (amount, card_id))
                cursor.execute("DELETE FROM savings_plans WHERE id=?", (plan_id,))
                
                log_transaction(cursor, conn, user_id, "savings_return", amount, f"Повернено при видаленні плану: {plan_name} на картку {selected_card['name']}")
                log_savings_transaction(cursor, conn, user_id, plan_id, amount, "plan_deleted", f"Видалено план з поверненням на картку {selected_card['name']}")
                
                conn.commit()
                self.clear_inputs()
                self.update_savings_tab()
                self._display_message(f"План успішно видалено! ${amount:.2f} повернуто на картку {selected_card['name']}.")
                self._update_home_tab()
            except Exception as e:
                self._display_message(f"Помилка видалення: {str(e)}", True)

        popup, _ = self._create_popup_content(
            title=f"Оберіть картку для повернення коштів",
            info_text=f"План: {plan_name}\nСума: ${amount:.2f}",
            button_text='ВИДАЛИТИ',
            callback_func=callback,
            is_destructive=True
        )
        if popup: popup.open()