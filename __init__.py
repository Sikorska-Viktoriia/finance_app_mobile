
from utils.db_manager import(
    conn, 
    cursor, 
    is_valid_email, 
    is_valid_password, 
    hash_password, 
    check_password,
    log_transaction, 
    get_user_cards, 
    debug_transactions, 
    get_total_balance,
    update_card_balance, 
    create_user_card, 
    update_user_card, 
    delete_user_card,
    transfer_money_between_cards, 
    log_savings_transaction, 
    get_user_envelopes,
    create_envelope, 
    add_to_envelope, 
    get_envelope_transactions, 
    get_envelope_stats,
    update_envelope, 
    get_analytics_data, 
    get_category_breakdown, 
    get_top_categories,
    get_cards_analytics, 
    get_budget_progress, 
    get_insights_and_forecasts,
    get_monthly_comparison, 
    save_profile_photo, 
    get_profile_photo,
    log_user_session, 
    log_user_logout, 
    get_login_history, 
    get_user_settings, 
    update_user_settings,
    get_user_level, 
    update_user_experience, 
    log_security_action, 
    get_user_by_email,
    get_user_savings_plans, 
    get_user_transactions,
    setup_db,
    safe_color_conversion  # Додано для повноти
)

# Хардкод списку функцій для __all__. Це гарантує, що
# ці імена будуть доступні при імпорті 'from utils import *'.
__all__ = [
    # Глобальні об'єкти
    'conn', 
    'cursor', 
    
    # Користувачі та безпека
    'is_valid_email', 
    'is_valid_password', 
    'hash_password', 
    'check_password', 
    'create_user', 
    'get_user_by_email',
    'log_user_session',
    'log_user_logout',
    'get_login_history',
    'log_security_action',
    
    # Картки та Баланс
    'create_user_card', 
    'get_user_cards', 
    'get_total_balance', 
    'update_card_balance', 
    'update_user_card',
    'delete_user_card', 
    'transfer_money_between_cards',
    'get_user_card_by_id',

    # Транзакції
    'log_transaction', 
    'get_user_transactions',
    'debug_transactions',
    
    # Конверти (Бюджетування)
    'create_envelope', 
    'get_user_envelopes', 
    'add_to_envelope', 
    'get_envelope_transactions',
    'get_envelope_stats', 
    'update_envelope',
    
    # Заощадження
    'log_savings_transaction',
    'get_user_savings_plans',

    # Аналітика
    'get_analytics_data', 
    'get_category_breakdown', 
    'get_top_categories',
    'get_cards_analytics', 
    'get_budget_progress', 
    'get_insights_and_forecasts', 
    'get_monthly_comparison',
    
    # Профіль та Налаштування
    'save_profile_photo', 
    'get_profile_photo',
    'get_user_settings', 
    'update_user_settings',
    'get_user_level', 
    'update_user_experience',
    'export_user_data',
    
    # Утиліти
    'setup_db',
    'safe_color_conversion'
]