import requests
from pyrogram import Client, filters, enums
from config import OCR_KEY, DATABASE_URL, LOG_CHANNEL
from pymongo import MongoClient
from modules.modles.ai_res import get_response
from modules.chatlogs import user_log
from modules.lang import get_ui_message, get_user_language
import os


mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

async def extract_text_res(bot, update):
    user_id = update.from_user.id
    processing_msg = await update.reply(get_ui_message("extracting_text", user_id))
    
    if update.caption:
        caption = update.caption[3:]
    else:
        caption = ""
    
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
        extracted_text = response_data["ParsedResults"][0]["ParsedText"]
    else:
        error_message = response_data["ErrorMessage"]
        error_text = get_ui_message("ocr_error", user_id) + f": {error_message}"
        await update.reply_photo(photo=file, caption=error_text + "\n" + get_ui_message("no_text_found", user_id))
        await processing_msg.delete()
        return
    
    extracted_text = extracted_text + caption
    await processing_msg.delete()

    try:
        ask = extracted_text 

        # Fetch user history from MongoDB
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history:
            history = user_history['history']
        else: 
            history = [
    {
        "role": "assistant",
        "content": (
            "I am an AI chatbot assistant, developed by CHANDAN SINGH(i.e.@TechyCSR) and a his dedicated team of students from Lovely Professional University (LPU). "
            "Our core team also includes Ankit and Aarushi who have all worked together to create a bot that facilitates user tasks and "
            "improves productivity in various ways. Our goal is to make interactions smoother and more efficient, providing accurate and helpful "
            "responses to your queries. The bot leverages the latest advancements in AI technology to offer features such as speech-to-text, "
            "text-to-speech, image generation, and more. Our mission is to continuously enhance the bot's capabilities, ensuring it meets the "
            "growing needs of our users. The current version is V-2.O, which includes significant improvements in response accuracy and speed, "
            "as well as a more intuitive user interface. We aim to provide a seamless and intelligent chat experience, making the AI assistant a "
            "valuable tool for users across various domains. To Reach out CHANDAN SINGH, you can contact him on techycsr.me or on his email csr.info.in@gmail.com"
        )
    }
]


        # Add the new user query to the history
        history.append({"role": "user", "content": ask})

        # Get the AI response
        ai_response = get_response(history)
        
        await bot.send_chat_action(chat_id=update.chat.id, action=enums.ChatAction.TYPING)

        
        # Add the AI response to the history
        history.append({"role": "assistant", "content": ai_response})

        # Update the user's history in MongoDB
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )

        # Get the translated completion message
        feature_notice = get_ui_message("beta_feature_notice", user_id)
        if feature_notice == "beta_feature_notice":
            feature_notice = "**Beta Version Feature @AdvChatGptBot**"
        
        # Reply to the user's message with the AI response
        await update.reply_text(ai_response + "\n\n" + feature_notice)
        
        # Log photo and text
        await bot.send_photo(chat_id=LOG_CHANNEL, photo=file)
        await user_log(bot, update, "#Image\n" + extracted_text + "\n" + ai_response)
        os.remove(file)

    except Exception as e:
        error_msg = get_ui_message("ai_processing_error", user_id)
        await update.reply_text(f"{error_msg}: {e}")
        print(f"Error in extract_text_res function: {e}")


