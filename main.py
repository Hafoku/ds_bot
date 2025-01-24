import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
import random
import google.generativeai as genai

# Настройка API Gemini
genai.configure(api_key="")
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

# Настройка логирования в папку logs
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', handlers=[
    logging.FileHandler(os.path.join(log_dir, 'bot.log'), encoding='utf-8'),
    logging.StreamHandler()
])

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
            await self.tree.sync()
            logging.info("Слэш-команды синхронизированы.")
            for command in self.tree.get_commands():
                logging.info(f"Зарегистрирована команда: {command.name}")
        except Exception as e:
            logging.error(f"Ошибка синхронизации слэш-команд: {e}")

# Инициализация бота
bot = MyBot()

@bot.event
async def on_ready():
    logging.info(f"Бот {bot.user} запущен и готов к работе!")
    await bot.change_presence(activity=discord.Game(name="Модерирую сервер"))
    for command in bot.tree.get_commands():
        logging.info(f"Команда доступна: {command.name}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if bot.user in message.mentions or message.reference:
        guild_name = message.guild.name if message.guild else "DMs"
        log_dir = f"logs/{guild_name}"
        content = (
            f"[{message.created_at}] {message.author} ({message.author.id}): "
            f"{message.clean_content}"
        )
        save_log(log_dir, "messages.log", content)

    await bot.process_commands(message)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.command:
        try:
            guild_name = interaction.guild.name if interaction.guild else "DMs"
            log_dir = f"logs/{guild_name}"

            filename = "requests.log" if interaction.command.name == "запрос" else "commands.log"
            content = (
                f"[{interaction.created_at}] {interaction.user} ({interaction.user.id}) "
                f"выполнил команду: {interaction.command.name}"
            )

            if interaction.data.get("options"):
                options = interaction.data["options"]
                params = ", ".join(
                    f"{option['name']}={option['value']}" for option in options
                )
                content += f" с параметрами: {params}"

            save_log(log_dir, filename, content)

        except Exception as e:
            logging.error(f"Ошибка логирования команды: {e}")

@bot.tree.command(name="запрос", description="Отправить запрос в Gemini API")
async def запрос(interaction: discord.Interaction, запрос: str):
    try:
        guild_name = interaction.guild.name if interaction.guild else "DMs"
        response = model.generate_content(запрос)
        result = response.text

        content = f"[{interaction.created_at}] {interaction.user} отправил запрос: {запрос}. Ответ: {result}"
        save_log(f"logs/{guild_name}", "requests.log", content)

        if len(result) > 2000:
            filename = f"response_{interaction.id}.txt"
            with open(os.path.join("logs", filename), "w", encoding="utf-8") as file:
                file.write(result)
            await interaction.response.send_message(
                f"Результат слишком длинный. Полный ответ сохранён в файле: `{filename}`."
            )
        else:
            await interaction.response.send_message(f"Результат запроса: {result}")
    except Exception as e:
        logging.error(f"Ошибка при запросе: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Ошибка: {e}")

@bot.tree.command(name="гемблинг", description="Попробуй удачу! Рискни!")
async def гемблинг(interaction: discord.Interaction):
    try:
        chance = random.uniform(0, 1000)
        if chance == 1:
            if interaction.guild and interaction.guild.me.guild_permissions.ban_members:
                if interaction.guild.me.top_role > interaction.user.top_role:
                    await interaction.user.ban(reason="Проиграл в гемблинге с шансом 0.1%")
                    await interaction.response.send_message(
                        f"Ебать ты чмо, {interaction.user.mention}! Ты проиграл и теперь забанен. 😵"
                    )
                else:
                    await interaction.response.send_message(
                        "Не могу забанить этого пользователя, у него роль выше моей."
                    )
            else:
                await interaction.response.send_message(
                    "Эту команду можно использовать только на сервере."
                )
        elif chance <= 500:
            await interaction.response.send_message(
                f"На этот раз повезло, {interaction.user.mention}! Ты победил! 🎉"
            )
        else:
            await interaction.response.send_message(
                f"Фу, лох, {interaction.user.mention}! Ты проиграл. 😂"
            )
    except Exception as e:
        logging.error(f"Ошибка в команде гемблинг: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"Произошла ошибка: {e}")

TOKEN = ""
bot.run(TOKEN)
