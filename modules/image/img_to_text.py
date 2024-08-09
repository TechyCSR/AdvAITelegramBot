
import requests
from pyrogram import Client, filters, enums
from config import OCR_KEY, DATABASE_URL
from pymongo import MongoClient
from modules.modles.ai_res import get_response

# Initialize the MongoDB client
mongo_client = MongoClient(DATABASE_URL)

# Access or create the database and collection
db = mongo_client['aibotdb']
history_collection = db['history']

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
        extracted_text = response_data["ParsedResults"][0]["ParsedText"]
    else:
        error_message = response_data["ErrorMessage"]
        text = f"Error: Failed to extract text from image. {error_message}"
        await update.reply_photo(photo=file, caption=text + "\nNo text found")
        return
    
    # Send the extracted text as a reply
    await processing_msg.delete()

    try:
        user_id = update.from_user.id
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
            "I am an AI chatbot assistant, developed by CSR(i.e.@TechyCSR) and a dedicated team of students from Lovely Professional University (LPU). "
            "Our core team also includes Ankit, Aarushi, and Yashvi, who have all worked together to create a bot that facilitates user tasks and "
            "improves productivity in various ways. Our goal is to make interactions smoother and more efficient, providing accurate and helpful "
            "responses to your queries. The bot leverages the latest advancements in AI technology to offer features such as speech-to-text, "
            "text-to-speech, image generation, and more. Our mission is to continuously enhance the bot's capabilities, ensuring it meets the "
            "growing needs of our users. The current version is V-1.0.1, which includes significant improvements in response accuracy and speed, "
            "as well as a more intuitive user interface. We aim to provide a seamless and intelligent chat experience, making the AI assistant a "
            "valuable tool for users across various domains."
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

        # Reply to the user's message with the AI response
        await update.reply_text(ai_response)

    except Exception as e:
        await update.reply_text(f"An error occurred: {e}")
        print(f"Error in aires function: {e}")


