import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = 'ВАШ_ТОКЕН_БОТА'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Работа с базой данных ---
def init_db():
    conn = sqlite3.connect('shopping_list.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- Состояния FSM ---
class ShoppingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_quantity = State()

# --- Главная клавиатура ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="🛒 Мои товары")],
            [KeyboardButton(text="🗑️ Удалить товар")]
        ],
        resize_keyboard=True
    )

# --- Старт ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот «Список покупок». Выберите нужное действие:",
        reply_markup=get_main_keyboard()
    )

# --- Добавление товара: Шаг 1 (Название) ---
@dp.message(F.text == "➕ Добавить товар")
async def add_item_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название товара:")
    await state.set_state(ShoppingState.waiting_for_name)

@dp.message(ShoppingState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите количество (или вес, например: 2 шт, 1 кг):")
    await state.set_state(ShoppingState.waiting_for_quantity)

@dp.message(ShoppingState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data['name']
    quantity = message.text

    conn = sqlite3.connect('shopping_list.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO products (name, quantity) VALUES (?, ?)', (name, quantity))
    conn.commit()
    conn.close()

    await message.answer(f"Товар «{name}» ({quantity}) успешно добавлен!", reply_markup=get_main_keyboard())
    await state.clear()

# --- Посмотреть список товаров ---
@dp.message(F.text == "🛒 Мои товары")
async def show_items(message: types.Message):
    conn = sqlite3.connect('shopping_list.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, quantity FROM products')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Ваш список покупок пуст.")
        return

    response = "🛒 **Ваш список покупок:**\n\n"
    for row in rows:
        response += f"ID: {row[0]} | **{row[1]}** — {row[2]}\n"
    
    await message.answer(response, parse_mode="Markdown")

# --- Удаление товара ---
@dp.message(F.text == "🗑️ Удалить товар")
async def delete_item_start(message: types.Message):
    conn = sqlite3.connect('shopping_list.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, quantity FROM products')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("Список пуст, нечего удалять.")
        return

    # Создаем инлайн-кнопки для каждого товара
    keyboard_buttons = []
    for row in rows:
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"❌ Удалить: {row[1]} ({row[2]})", callback_data=f"del_{row[0]}")
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer("Выберите товар для удаления:", reply_markup=markup)

@dp.callback_query(F.data.startswith("del_"))
async def delete_item_callback(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])

    conn = sqlite3.connect('shopping_list.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    await callback.message.edit_text("Товар успешно удален из списка!")
    await callback.answer()

# --- Запуск бота ---
if __name__ == '__main__':
    import asyncio
    async def main():
        await dp.start_polling(bot)
    asyncio.run(main())