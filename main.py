import csv
import os
import io
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot_token = '5938916690:AAHOOZ08Cxf3ARylBtqDk4fMJqtB0lOwPLk'
bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализация базы данных SQLite
conn = sqlite3.connect('registration.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    email TEXT
    status TEXT
)
''')
conn.commit()


# Определение состояний для FSM
class RegistrationForm(StatesGroup):
    name = State()
    age = State()
    email = State()
    done = State()


# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    # Проверяем статус пользователя в базе данных
    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()
    if user:
        # Если пользователь уже зарегистрирован, выводим сообщение
        await message.answer('Вы уже зарегистрированы.')
    else:
        # Если пользователь не зарегистрирован, начинаем регистрацию
        await message.answer('Привет! Чтобы зарегистрироваться, ответь на несколько вопросов. Как тебя зовут?')
        await RegistrationForm.name.set()


# Обработчик ответа на вопрос "Как тебя зовут?"
@dp.message_handler(state=RegistrationForm.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
        await message.answer('Сколько тебе лет?')
        await RegistrationForm.age.set()


# Обработчик ответа на вопрос "Сколько тебе лет?"
@dp.message_handler(lambda message: not message.text.isdigit(), state=RegistrationForm.age)
async def process_age_invalid(message: types.Message):
    await message.answer("Пожалуйста, введи свой возраст цифрами.")


@dp.message_handler(lambda message: message.text.isdigit(), state=RegistrationForm.age)
async def process_age(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['age'] = int(message.text)
        await message.answer('Какой у тебя email?')
        await RegistrationForm.email.set()


# Обработчик ответа на вопрос "Какой у тебя email?"
@dp.message_handler(state=RegistrationForm.email)
async def process_email(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['email'] = message.text
        # Сохраняем данные в базе данных и устанавливаем статус пользователя "done"
        cursor.execute("INSERT INTO users (user_id, name, age, email, status) VALUES (?, ?, ?, ?, ?)",
                       (message.from_user.id, data['name'], data['age'], data['email'], "done"))
        conn.commit()
        # Отправляем сообщение об успешной регистрации
        await message.answer('Спасибо за регистрацию!')
        # Сбрасываем состояние FSM
        await state.finish()


# Функция для проверки прав администратора
async def check_admin(user_id: int) -> bool:
    admins = [707305173, 150429627]  # список администраторов
    return user_id in admins


# Функция для отправки содержимого базы данных в CSV-формате
@dp.message_handler(commands=['csv'])
async def send_csv_file(message: types.Message):
    if not await check_admin(message.from_user.id):
        await message.answer("Вы не являетесь администратором.")
        return

    # Получаем данные из базы данных
    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()

    # Создаем CSV-файл в памяти
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(('user_id', 'name', 'age', 'email'))  # заголовки столбцов
    for row in data:
        writer.writerow(row)

    # Отправляем CSV-файл в сообщении
    output.seek(0)  # переводим указатель на начало файла
    filename = "user.csv"
    with open(filename, "w", newline="") as file:
        file.write(output.getvalue())
    await message.answer_document(open(filename, "rb"))
    os.remove(filename)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
