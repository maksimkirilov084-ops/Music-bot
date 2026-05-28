import os
import asyncio
import yt_dlp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from googleapiclient.discovery import build
from config import BOT_TOKEN, YOUTUBE_API_KEY

# YouTube
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Тексты
START_TEXT = "Welcome ✌️\nВведите название трека для поиска."
NOT_FOUND = "Хм, ничего не нашлось."
API_ERROR = "Я споткнулся. Дай мне минутку."
SHORT_QUERY = "Напиши хотя бы пару слов."
FILE_TOO_BIG = "Трек слишком большой."
WAITING = "Ищу..."

# Бот
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

def search_tracks(query):
    request = youtube.search().list(q=query, part="snippet", type="video", maxResults=5, videoCategoryId="10")
    response = request.execute()
    results = []
    for item in response.get("items", []):
        results.append({"id": item["id"]["videoId"], "title": item["snippet"]["title"], "channel": item["snippet"]["channelTitle"]})
    return results

@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer(START_TEXT)

@router.message()
async def search(message: types.Message):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer(SHORT_QUERY)
        return
    try:
        tracks = search_tracks(query)
    except:
        await message.answer(API_ERROR)
        return
    if not tracks:
        await message.answer(NOT_FOUND)
        return
    buttons = []
    for t in tracks:
        buttons.append([InlineKeyboardButton(text=f"{t['title'][:40]} — {t['channel']}", callback_data=f"dl_{t['id']}")])
    await message.answer("Вот что я нашёл:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(lambda c: c.data.startswith("dl_"))
async def download(callback: types.CallbackQuery):
    vid = callback.data.replace("dl_", "")
    await callback.answer(WAITING)
    try:
        ydl_opts = {"format": "bestaudio/best", "outtmpl": f"{vid}.%(ext)s", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}], "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={vid}"])
        path = f"{vid}.mp3"
        if os.path.getsize(path) > 50_000_000:
            await callback.message.answer(FILE_TOO_BIG)
        else:
            await callback.message.answer_audio(FSInputFile(path))
        os.remove(path)
    except:
        await callback.message.answer(API_ERROR)

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
