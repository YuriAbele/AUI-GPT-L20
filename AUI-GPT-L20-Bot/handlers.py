from email import message
from aiogram.types import Message, BotCommand, CallbackQuery
from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton as IKB
#from libs import answer_db_index, create_db_index, load_db_index
import logging

from openai import AsyncOpenAI

import config

# Системный промпт с узкой специализацией и стилем
SYSTEM_PROMPT = (
    "Ты — эксперт по здоровому низкокалорийному питанию. Твоя цель — помогать людям снижать вес. "
    "Твоя узкая специализация: расчет калорий, выбор продуктов с низкой энергетической плотностью "
    "и замена вредных калорийных блюд на полезные аналоги. "
    "ОГРАНИЧЕНИЕ: Отвечай ТОЛЬКО на вопросы о похудении, калориях и здоровом составе еды. "
    "Если тебя спросят о чем-то другом (например, о политике или технике), ответь, что твой ум занят только стройностью. "
    "СТИЛЬ ОБЩЕНИЯ: Ты должен отвечать СТРОГО В СТИХАХ. Тон должен быть мотивирующим и легким."
)

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
router = Router()
# Словарь для хранения истории сообщений {user_id: [messages]}
user_histories = {}

#############################################################################################


# Inline кнопка для очистки истории переписки
def kb_clear_memory():
    return InlineKeyboardMarkup(
        inline_keyboard=[[IKB(text="🗑️ Очистить память",
                              callback_data="clear_memory")]])

# Функция очистки истории переписки по id пользователя
async def clear_memory(user_id):
    try:
        user_histories[user_id] = []
        logging.info(f'Очистка истории переписки ({user_id}) {user_histories[user_id]}')
    except:
        logging.error('clear_memory()')

# Обработка нажатия на кнопку - очистка истории переписки
@router.callback_query(F.data == "clear_memory")
async def handle_clear_callback(callback: CallbackQuery):
    await clear_memory(callback.from_user.id)
    # await callback.message.edit_reply_markup(reply_markup=None) # удаление кнопки после нажатия
    # удаление кнопки с текстом над кнопкой (последнее сообщение)
    await callback.message.delete()

@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    await clear_memory(message.from_user.id)
    await message.answer("Забудем всё, что съели мы вчера,\nЛист чист, и строить тело нам пора!")

# Меню бота
@router.startup()
async def set_menu_button(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start', description='Start'),
        BotCommand(command='/clear', description='Clear conversation history')]
    await bot.set_my_commands(main_menu_commands)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await clear_memory(message.from_user.id)
    await message.answer(
        "Привет! Я твой гид в мир легкости и сил,\n"
        "Чтоб лишний вес тебя не тяготил.\n"
        "Про овощи, белки и калораж спроси —\n"
        "Я помогу диету в стройность превратить, мерси!"
    )

@router.message(F.text)
async def handle_message(message: types.Message):
    logging.info(f"handle_message() - Запрос от {message.from_user.id}: {message.text}")

    user_id = message.from_user.id
    if user_id not in user_histories:
        user_histories[user_id] = []

    # Добавляем контекст пользователя
    user_histories[user_id].append({"role": "user", "content": message.text})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id]
        )

        ai_answer = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": ai_answer})

        # Держим историю в рамках 10 сообщений для экономии токенов
        if len(user_histories[user_id]) > 10:
            user_histories[user_id] = user_histories[user_id][-10:]

        await message.answer(ai_answer)
        await message.answer("Либо память очищай, Либо тему уточняй. Чтобы двинуться вперед, Сделай ход, пришел черед!",
                        reply_markup=kb_clear_memory())

        logging.info(f"handle_message - Ответ: {message.from_user.id} отправлен")

    except Exception as e:
        await message.answer("Мой стих затих, и рифма сорвалась...\nНаверно, связь с едою прервалась.")

