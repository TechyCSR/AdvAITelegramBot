import os
import docx
import pdfplumber
import json
import csv
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from modules.models.ai_res import DEFAULT_SYSTEM_MESSAGE
from modules.core.database import get_history_collection
from modules.user.premium_management import is_user_premium
from config import ADMINS
from pyrogram.enums import ParseMode
from modules.core.request_queue import (
    can_start_text_request, 
    start_text_request, 
    finish_text_request
)

SUPPORTED_TEXT_EXTENSIONS = [
    ".txt", ".md", ".json", ".csv", ".xml", ".html", ".css", ".js", ".py", ".sh", ".log", ".yaml", ".sql"
]
SUPPORTED_BINARY_EXTENSIONS = [
    ".pdf", ".docx"
]
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS + SUPPORTED_BINARY_EXTENSIONS

# Helper to extract text from file

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext in [".txt", ".md", ".css", ".js", ".py", ".sh", ".log", ".yaml", ".sql"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                return "\n".join([", ".join(row) for row in reader])
        elif ext == ".xml" or ext == ".html":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif ext == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            return None
    except Exception as e:
        return f"[Error reading file: {e}]"

async def handle_file_upload(client, message: Message):
    user_id = message.from_user.id
    is_premium, _, _ = await is_user_premium(user_id)
    is_admin = user_id in ADMINS
    if not message.document:
        await message.reply_text("Please send a file (document) to use this feature.")
        return
    filename = message.document.file_name
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALL_SUPPORTED_EXTENSIONS:
        await message.reply_text(
            f"❌ Unsupported file type: {ext}\n\n" +
            "Supported file types are:\n" +
            ", ".join(ALL_SUPPORTED_EXTENSIONS)
        )
        return
    # Show waiting message
    wait_msg = await message.reply_text("⏳ Extracting text from your file, please wait...")
    # Download the file
    file_path = await client.download_media(message.document)
    # Extract text
    text = extract_text_from_file(file_path)
    # Clean up local file
    try:
        os.remove(file_path)
    except Exception:
        pass
    if not text or text.strip() == "":
        await wait_msg.edit_text("❌ Could not extract any text from this file.")
        return
    # Save to user history (like ai_res)
    history_collection = get_history_collection()
    user_history = history_collection.find_one({"user_id": user_id})
    if user_history and 'history' in user_history:
        history = user_history['history']
        if not isinstance(history, list):
            history = [history]
    else:
        history = DEFAULT_SYSTEM_MESSAGE.copy()
    prompt = f"A file was uploaded: {filename}. Extracted text is below."
    history.append({"role": "user", "content": prompt})
    history.append({"role": "user", "content": text[:4000]})
    history_collection.update_one(
        {"user_id": user_id},
        {"$set": {"history": history}},
        upsert=True
    )
    # Show preview if text is long
    preview = text[:2000]
    if len(text) > 2000:
        preview += "\n...\n[truncated]"
    await wait_msg.edit_text(
        f"✅ File uploaded and text extracted!\n\nPreview:\n<pre>{preview}</pre>\n\nYou can now continue by sending your question about this file.",
        parse_mode=ParseMode.HTML
    )

async def handle_file_question(client, message: Message):
    user_id = message.from_user.id
    
    # Check if user can start a new text request
    can_start, queue_message = await can_start_text_request(user_id)
    if not can_start:
        await message.reply_text(queue_message)
        return
    
    try:
        # Start the text request in queue system
        start_text_request(user_id, f"File question: {message.text[:30]}...")
        
        # Find the most recent file text from user history
        history_collection = get_history_collection()
        user_history = history_collection.find_one({"user_id": user_id})
        file_text = None
        if user_history and 'history' in user_history:
            for entry in reversed(user_history['history']):
                if isinstance(entry.get("content"), str) and len(entry["content"]) > 20:
                    file_text = entry["content"]
                    break
        if not file_text:
            await message.reply_text("No uploaded file found in your recent history. Please upload a file first.")
            return
        # Compose the message for AI
        user_question = message.text
        from g4f.client import Client
        import g4f.debug
        g4f.debug.logging = True
        client_g4f = Client()
        g4f_messages = [
            {"role": "user", "content": [
                {"type": "text", "text": f"{user_question}\n\n[file content follows]\n{file_text[:4000]}"}
            ]}
        ]
        try:
            response = client_g4f.chat.completions.create(g4f_messages)
            ai_response = response.choices[0].message.content
        except Exception as e:
            await message.reply_text(f"Error processing file with AI: {e}")
            return
        # Save to history
        user_history = history_collection.find_one({"user_id": user_id})
        if user_history and 'history' in user_history:
            history = user_history['history']
            if not isinstance(history, list):
                history = [history]
        else:
            history = DEFAULT_SYSTEM_MESSAGE.copy()
        history.append({"role": "user", "content": user_question})
        history.append({"role": "assistant", "content": ai_response})
        history_collection.update_one(
            {"user_id": user_id},
            {"$set": {"history": history}},
            upsert=True
        )
        await message.reply_text(ai_response)
    finally:
        # Always finish the text request in queue system
        finish_text_request(user_id) 