
import requests
from pyrogram import Client, filters
from config import OCR_KEY

async def extract_text_res(bot, update):
    processing_msg = await update.reply("ᴇxᴛʀᴀᴄᴛɪɴɢ ᴛᴇxᴛ ꜰʀᴏᴍ ɪᴍᴀɢᴇ...")

    # Get the largest available version of the image
    if isinstance(update.photo, list):
        photo = update.photo[-1]
    else:
        photo = update.photo

    # Download the image file
    file = await bot.download_media(photo.file_id)

    # Upload the image file to the OCR.Space API
    url = "https://api.ocr.space/parse/image"
    headers = {"apikey": OCR_KEY}
    with open(file, "rb") as image_file:
        response = requests.post(url, headers=headers, files={"image": image_file})

    # Parse the API response to extract the extracted text
    response_data = response.json()
    if response_data["IsErroredOnProcessing"] == False:
        text = response_data["ParsedResults"][0]["ParsedText"]
    else:
        error_message = response_data["ErrorMessage"]
        text = f"Error: Failed to extract text from image. {error_message}"
        await update.reply_photo(photo=file, caption=text + "\nNo text found")
        return
    
    # Send the extracted text as a reply
    await update.reply_text(text)
    await processing_msg.delete()
