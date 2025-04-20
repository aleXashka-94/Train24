import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# Временное хранилище поездок (можно заменить на базу данных)
trips = []

# Кнопки
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(
    KeyboardButton("Сегодня"), KeyboardButton("Вчера"), KeyboardButton("Указать дату вручную")
)

# Начало
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer("Привет, выбери дату явки:", reply_markup=main_kb)

# Выбор даты
@dp.message_handler(lambda m: m.text in ["Сегодня", "Вчера", "Указать дату вручную"])
async def date_choice_handler(message: types.Message):
    if message.text == "Сегодня":
        chosen_date = datetime.now()
        await message.answer(f"Ты выбрал: {chosen_date.strftime('%d.%m.%Y')}\n\nВведи время явки (например: 08:30):")
        dp.current_state(user=message.from_user.id).update_data(date=chosen_date.date())
    elif message.text == "Вчера":
        chosen_date = datetime.now() - timedelta(days=1)
        await message.answer(f"Ты выбрал: {chosen_date.strftime('%d.%m.%Y')}\n\nВведи время явки (например: 08:30):")
        dp.current_state(user=message.from_user.id).update_data(date=chosen_date.date())
    else:
        await message.answer("Введи дату вручную в формате: ДД.ММ.ГГГГ")

# Ввод времени и дальнейшая логика
@dp.message_handler()
async def generic_handler(message: types.Message):
    user_data = await dp.current_state(user=message.from_user.id).get_data()
    
    if 'date' in user_data:
        try:
            time_obj = datetime.strptime(message.text.strip(), "%H:%M").time()
            full_datetime = datetime.combine(user_data['date'], time_obj)
            await message.answer(f"Принято время явки: {full_datetime.strftime('%d.%m.%Y %H:%M')}\n\nТеперь введи время сдачи (например: 19:45):")
            await dp.current_state(user=message.from_user.id).update_data(start=full_datetime)
        except:
            await message.answer("Неверный формат времени. Введи в формате ЧЧ:ММ (например: 08:30)")
    elif 'start' in user_data:
        try:
            time_obj = datetime.strptime(message.text.strip(), "%H:%M").time()
            end_datetime = datetime.combine(datetime.now().date(), time_obj)
            if end_datetime < user_data['start']:
                end_datetime += timedelta(days=1)  # если сдача после полуночи
            await dp.current_state(user=message.from_user.id).update_data(end=end_datetime)

            # Расчёты
            duration = end_datetime - user_data['start']
            duration_hours = duration.total_seconds() / 3600

            # Ночные часы (22:00–06:00)
            night_hours = 0
            current = user_data['start']
            while current < end_datetime:
                if 22 <= current.hour or current.hour < 6:
                    night_hours += 1
                current += timedelta(hours=1)

            # Переотдых (если между поездками > 6 часов — здесь просто выводим)
            trip = {
                "start": user_data['start'],
                "end": end_datetime,
                "duration": round(duration_hours, 2),
                "night_hours": night_hours
            }
            trips.append(trip)

            msg = (
                f"Поездка сохранена:\n"
                f"Явка: {user_data['start'].strftime('%d.%m.%Y %H:%M')}\n"
                f"Сдача: {end_datetime.strftime('%d.%m.%Y %H:%M')}\n"
                f"Общее время: {round(duration_hours, 2)} ч\n"
                f"Ночных часов: {night_hours}"
            )
            await message.answer(msg)
        except:
            await message.answer("Неверный формат времени. Введи в формате ЧЧ:ММ")

# Статистика
@dp.message_handler(commands=['stat'])
async def stat_handler(message: types.Message):
    total = sum(trip['duration'] for trip in trips)
    night_total = sum(trip['night_hours'] for trip in trips)
    await message.answer(f"Всего поездок: {len(trips)}\nОбщее время: {round(total,2)} ч\nНочных: {night_total} ч")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)