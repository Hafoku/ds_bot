import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
import random
import google.generativeai as genai
import requests  # Добавляем импорт для работы с HTTP-запросами

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
@bot.tree.command(name="гемини", description="Отправить запрос гемини")
async def гемини(interaction: discord.Interaction, гемини: str):
    try:
        # Подтверждаем интеракцию
        await interaction.response.defer()

        # Получение имени сервера или указание на ЛС
        guild_name = interaction.guild.name if interaction.guild else "DMs"

        # Отправка запроса в API Gemini
        try:
            response = model.generate_content(гемини)  # Генерация контента на основе запроса
            result = response.text if hasattr(response, 'text') else None
        except Exception as api_error:
            logging.error(f"Ошибка API Gemini: {api_error}")
            await interaction.followup.send(f"Ошибка API: {api_error}")
            return

        if not result:
            logging.warning("Пустой ответ от API Gemini.")
            await interaction.followup.send("API вернул пустой ответ. Попробуйте снова.")
            return

        # Директория для сохранения логов ответов
        response_dir = f"logs/{guild_name}/responses"
        ensure_dir_exists(response_dir)  # Убедиться, что директория существует

        if len(result) > 2000:
            # Если длина ответа превышает 2000 символов, сохраняем его в файл
            try:
                existing_files = os.listdir(response_dir)
                count = sum(1 for file in existing_files if file.startswith("ответ")) + 1
                filename = f"ответ{count}.txt"  # Уникальное имя файла
                file_path = os.path.join(response_dir, filename)

                # Запись ответа в файл
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(result)

                # Отправка файла в ответ пользователю
                with open(file_path, "rb") as file:
                    await interaction.followup.send(
                        "Результат слишком длинный. Полный ответ сохранён в файле:",
                        file=discord.File(file, filename=filename)
                    )

                # Логирование успешного сохранения
                logging.info(f"Ответ сохранён в файл: {file_path}")
            except Exception as file_error:
                logging.error(f"Ошибка записи файла: {file_error}")
                await interaction.followup.send(f"Ошибка сохранения файла: {file_error}")
                return
        else:
            # Если длина ответа менее 2000 символов, отправляем его как текст
            await interaction.followup.send(f"Результат запроса: {result}")

        # Логирование успешного запроса
        content = (
            f"[{interaction.created_at}] {interaction.user} отправил запрос: {гемини}. "
            f"Ответ сохранён в: {filename if len(result) > 2000 else 'сообщении.'}"
        )
        save_log(f"logs/{guild_name}", "requests.log", content)

    except Exception as e:
        # Обработка ошибок
        logging.error(f"Ошибка при запросе: {e}")
        if not interaction.response.is_done():
            await interaction.followup.send(f"Ошибка: {e}")

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


@bot.tree.command(name="дипсик", description="Отправить запрос к DeepSeek R1")
async def дипсик(interaction: discord.Interaction, запрос: str):  # Измените название функции
    try:
        await interaction.response.defer()
        guild_name = interaction.guild.name if interaction.guild else "DMs"

        # Формируем запрос к OpenRouter API
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": запрос}],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content']
        except Exception as api_error:
            logging.error(f"Ошибка OpenRouter API: {api_error}")
            await interaction.followup.send(f"Ошибка API: {api_error}")
            return

        # Обработка и отправка результата (аналогично команде гемини)
        response_dir = f"logs/{guild_name}/responses"
        ensure_dir_exists(response_dir)

        if len(result) > 2000:
            try:
                existing_files = os.listdir(response_dir)
                count = sum(1 for file in existing_files if file.startswith("deepseek_response")) + 1
                filename = f"deepseek_response{count}.txt"
                file_path = os.path.join(response_dir, filename)

                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(result)

                with open(file_path, "rb") as file:
                    await interaction.followup.send(
                        "Результат слишком длинный. Полный ответ сохранён в файле:",
                        file=discord.File(file, filename=filename)
                    )

                logging.info(f"Ответ DeepSeek сохранён в файл: {file_path}")
            except Exception as file_error:
                logging.error(f"Ошибка записи файла: {file_error}")
                await interaction.followup.send(f"Ошибка сохранения файла: {file_error}")
                return
        else:
            await interaction.followup.send(f"Результат запроса: {result}")

        # Логирование
        content = (
            f"[{interaction.created_at}] {interaction.user} отправил DeepSeek запрос: {запрос}. "
            f"Ответ сохранён в: {filename if len(result) > 2000 else 'сообщении.'}"
        )
        save_log(f"logs/{guild_name}", "deepseek_requests.log", content)

    except Exception as e:
        logging.error(f"Ошибка при запросе к DeepSeek: {e}")
        if not interaction.response.is_done():
            await interaction.followup.send(f"Ошибка: {e}")

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("Команды синхронизированы!")

TOKEN = ""
bot.run(TOKEN)
