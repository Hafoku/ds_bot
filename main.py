import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
import random  # Для команды гемблинга
import google.generativeai as genai

# Настройка API Gemini
genai.configure(api_key="lorex_gemini_api")
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Настройка логирования в папку logs
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', handlers=[
    logging.FileHandler(os.path.join(log_dir, 'bot.log'), encoding='utf-8'),
    logging.StreamHandler()
])

# Настройка интентов
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

# Создание клиента Discord
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            # Очистка старых команд и синхронизация
            await self.tree.sync()
            logging.info("Слэш-команды синхронизированы.")

            # Отображение всех зарегистрированных команд
            for command in self.tree.get_commands():
                logging.info(f"Зарегистрирована команда: {command.name}")
        except Exception as e:
            logging.error(f"Ошибка синхронизации слэш-команд: {e}")

# Инициализация бота
bot = MyBot()

# Событие: бот готов
@bot.event
async def on_ready():
    logging.info(f"Бот {bot.user} запущен и готов к работе!")
    await bot.change_presence(activity=discord.Game(name="Модерирую сервер"))

    # Проверка регистрации команд
    for command in bot.tree.get_commands():
        logging.info(f"Команда доступна: {command.name}")

# Функция для создания директорий
def ensure_dir_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Функция для сохранения логов
def save_log(directory, filename, content):
    ensure_dir_exists(directory)
    file_path = os.path.join(directory, filename)
    with open(file_path, "a", encoding="utf-8") as file:
        file.write(content + "\n")
    logging.info(content)  # Дублирование в консоль

# Команда: запрос
@bot.tree.command(name="запрос", description="Отправить запрос в Gemini API")
async def запрос(interaction: discord.Interaction, запрос: str):
    try:
        # Проверяем, откуда запрос
        guild_name = interaction.guild.name if interaction.guild else "DMs"

        # Отправляем запрос в API
        response = model.generate_content(запрос)
        result = response.text  # Получаем текст ответа

        # Логируем запрос и ответ
        content = f"[{interaction.created_at}] {interaction.user} отправил запрос: {запрос}. Ответ: {result}"
        save_log(f"logs/{guild_name}/requests", "requests.log", content)

        # Отправляем ответ пользователю
        await interaction.response.send_message(f"Результат запроса: {result}")
    except Exception as e:
        logging.error(f"Ошибка при запросе: {e}")
        await interaction.response.send_message(f"Ошибка: {e}")

# Команда: кик
@bot.tree.command(name="кик", description="Кикнуть пользователя с сервера")
async def кик(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Пользователь {member} был кикнут. Причина: {reason}")
    else:
        await interaction.response.send_message("У вас нет прав на кик пользователей.")

# Команда: бан
@bot.tree.command(name="бан", description="Забанить пользователя на сервере")
async def бан(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"Пользователь {member} был забанен. Причина: {reason}")
    else:
        await interaction.response.send_message("У вас нет прав на бан пользователей.")

# Команда: варн
@bot.tree.command(name="варн", description="Выдать предупреждение пользователю")
async def варн(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    # Здесь можно реализовать логику варнинга (например, сохранять предупреждения в базе данных)
    await interaction.response.send_message(f"Пользователю {member} выдано предупреждение. Причина: {reason}")

# Команда: гемблинг
@bot.tree.command(name="гемблинг", description="Попробуй удачу! Рискни!")
async def гемблинг(interaction: discord.Interaction, member: discord.Member):
    try:
        result = random.randint(1, 2)  # Генерируем случайное число (1 или 2)
        if result == 1:
            # Мьютим пользователя на 30 минут
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if mute_role:
                await member.add_roles(mute_role, reason="Проиграл в гемблинге")
                await interaction.response.send_message(f"Не повезло, {member.mention}! Вы замьючены на 30 минут.")
                # Через 30 минут снимаем мут
                await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(minutes=30))
                await member.remove_roles(mute_role, reason="Мут снят после 30 минут")
            else:
                await interaction.response.send_message("Роль 'Muted' не найдена. Добавьте её на сервер.")
        else:
            # Пользователь выигрывает
            await interaction.response.send_message(f"Поздравляем, {member.mention}! Вы победили!")
    except Exception as e:
        logging.error(f"Ошибка в команде гемблинг: {e}")
        await interaction.response.send_message(f"Произошла ошибка: {e}")

# Запуск бота
TOKEN = "token_ds"
bot.run(TOKEN)
