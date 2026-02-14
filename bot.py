import os
import json
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Файл для хранения данных
DATA_FILE = 'bot_data.json'

# Шаблоны по умолчанию
DEFAULT_TEMPLATES = {
    'course_updated': '✅ Курс обновлён:\n{course}',
    'course_response': '📊 Актуальный курс:\n{course}',
    'template_updated': '✅ Шаблон "{template_name}" обновлён!',
    'templates_list': '📝 Доступные шаблоны:\n\n{templates}\n\nИспользуйте: /settemplate <название> <текст>\nВ тексте используйте {{course}} для подстановки курса'
}

# Функция для загрузки данных
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'course': 'Курс ещё не установлен',
        'templates': DEFAULT_TEMPLATES.copy()
    }

# Функция для сохранения данных
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Функция для получения курса
def get_course():
    data = load_data()
    return data.get('course', 'Курс ещё не установлен')

# Функция для сохранения курса
def save_course(course_text):
    data = load_data()
    data['course'] = course_text
    save_data(data)

# Функция для получения шаблона
def get_template(template_name):
    data = load_data()
    templates = data.get('templates', DEFAULT_TEMPLATES)
    return templates.get(template_name, DEFAULT_TEMPLATES.get(template_name, ''))

# Функция для сохранения шаблона
def save_template(template_name, template_text):
    data = load_data()
    if 'templates' not in data:
        data['templates'] = DEFAULT_TEMPLATES.copy()
    data['templates'][template_name] = template_text
    save_data(data)

# Команда для просмотра шаблонов
async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    is_admin = chat_member.status in ['creator', 'administrator']
    
    if not is_admin:
        await update.message.reply_text("⛔ Эта команда доступна только администраторам")
        return
    
    data = load_data()
    templates = data.get('templates', DEFAULT_TEMPLATES)
    
    templates_text = ""
    for name, template in templates.items():
        templates_text += f"▪️ <b>{name}</b>:\n<code>{template}</code>\n\n"
    
    message = get_template('templates_list').format(templates=templates_text)
    await update.message.reply_text(message, parse_mode='HTML')

# Команда для установки шаблона
async def settemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    is_admin = chat_member.status in ['creator', 'administrator']
    
    if not is_admin:
        await update.message.reply_text("⛔ Эта команда доступна только администраторам")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: /settemplate <название> <текст>\n\n"
            "Доступные шаблоны:\n"
            "▪️ course_updated - сообщение при обновлении курса админом\n"
            "▪️ course_response - сообщение при запросе курса пользователем\n\n"
            "Пример:\n"
            "/settemplate course_response 💱 Курс на сегодня: {course}\n\n"
            "Используйте {course} для подстановки курса"
        )
        return
    
    template_name = context.args[0]
    template_text = ' '.join(context.args[1:])
    
    # Проверяем, что это известный шаблон
    valid_templates = ['course_updated', 'course_response']
    if template_name not in valid_templates:
        await update.message.reply_text(
            f"❌ Неизвестный шаблон: {template_name}\n\n"
            f"Доступные шаблоны: {', '.join(valid_templates)}"
        )
        return
    
    save_template(template_name, template_text)
    
    message = get_template('template_updated').format(template_name=template_name)
    await update.message.reply_text(message)
    
    # Показываем пример
    example = template_text.format(course="USD = 75.50 ₽")
    await update.message.reply_text(f"Пример:\n{example}")

# Команда сброса шаблонов
async def resettemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    is_admin = chat_member.status in ['creator', 'administrator']
    
    if not is_admin:
        await update.message.reply_text("⛔ Эта команда доступна только администраторам")
        return
    
    data = load_data()
    data['templates'] = DEFAULT_TEMPLATES.copy()
    save_data(data)
    
    await update.message.reply_text("✅ Все шаблоны сброшены к значениям по умолчанию")

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    
    # Проверяем, что сообщение из группы
    if message.chat.type not in ['group', 'supergroup']:
        return
    
    text = message.text if message.text else ''
    user = message.from_user
    
    # Проверяем, является ли пользователь администратором
    chat_member = await context.bot.get_chat_member(message.chat_id, user.id)
    is_admin = chat_member.status in ['creator', 'administrator']
    
    # Если админ пишет сообщение, сохраняем как новый курс
    if is_admin:
        # Сохраняем весь текст сообщения как курс
        save_course(text)
        logger.info(f"Админ {user.username} обновил курс: {text}")
        
        # Используем шаблон для ответа
        response = get_template('course_updated').format(course=text)
        await message.reply_text(response)
    
    # Если обычный пользователь пишет слово "курс", отправляем последний курс
    elif 'курс' in text.lower():
        current_course = get_course()
        
        # Используем шаблон для ответа
        response = get_template('course_response').format(course=current_course)
        await message.reply_text(response)
        logger.info(f"Пользователь {user.username} запросил курс")

# Главная функция
def main():
    # Получаем токен бота из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения!")
    
    # Создаём приложение
    application = Application.builder().token(token).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("templates", templates_command))
    application.add_handler(CommandHandler("settemplate", settemplate_command))
    application.add_handler(CommandHandler("resettemplate", resettemplate_command))
    
    # Добавляем обработчик всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен!")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
