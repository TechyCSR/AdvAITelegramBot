import streamlit as st
from streamlit.components.v1 import html
from run import advAiBot

# Set up page configuration
st.set_page_config(
    page_title="AI ChatBot - Home",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define CSS for dark theme and modern look
CSS = """
<style>
body {
    font-family: 'Arial', sans-serif;
    background-color: #121212;
    color: #e0e0e0;
    text-align: center;
}
header {
    background-color: #1e1e1e;
    padding: 20px;
    border-radius: 15px;
    margin: 20px auto;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.8);
}
.container {
    margin: 20px auto;
    max-width: 80%;
    background-color: #1e1e1e;
    border-radius: 15px;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.8);
    padding: 30px;
    text-align: center;
}
h1 {
    color: #03a9f4;
    text-shadow: 0px 4px 10px rgba(3, 169, 244, 0.6);
}
h2 {
    color: #8bc34a;
    text-shadow: 0px 2px 6px rgba(139, 195, 74, 0.5);
}
a {
    color: #fbc02d;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
    color: #ffeb3b;
}
.button {
    display: inline-block;
    background: linear-gradient(to right, #4caf50, #03a9f4);
    color: white;
    padding: 15px 30px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    border-radius: 30px;
    text-shadow: 0 3px 6px rgba(0, 0, 0, 0.5);
    margin: 10px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.button:hover {
    background: linear-gradient(to right, #03a9f4, #4caf50);
    cursor: pointer;
    transform: scale(1.05);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.6);
}
ul {
    list-style: none;
    padding: 0;
}
li {
    margin: 10px 0;
    font-size: 18px;
}
</style>
"""

# Add CSS to the Streamlit app
st.markdown(CSS, unsafe_allow_html=True)

# Page Header
st.markdown(
    """
<header>
    <h1>✨ AI ChatBot Home Page ✨</h1>
    <p>Welcome to @AdvChatGptBot! Explore cutting-edge AI-powered features tailored for you.</p>
</header>
""",
    unsafe_allow_html=True,
)

# Main content container
st.markdown('<div class="container">', unsafe_allow_html=True)

st.markdown(
    """
<h2>Core Features</h2>
<ul>
    <li><b>AI ChatBot (GPT-4o and GPT-4o-mini)</b> - Engage in dynamic, context-aware conversations</li>
    <li><b>AI Speech to Text & Vice Versa</b> - Seamlessly convert speech to text and vice versa</li>
    <li><b>AI Generative Images (DALL-E 3 Model)</b> - Transform your ideas into stunning visuals</li>
    <li><b>AI Image to Text (Google Lens)</b> - Extract insights and text from any image</li>
</ul>

<h2>Customization Options</h2>
<ul>
    <li><b>🌐 Language Preferences</b> - Communicate in your preferred language</li>
    <li><b>🔔 Smart Notifications</b> - Tailor alerts to your needs</li>
    <li><b>🔒 Privacy Controls</b> - Manage your data securely</li>
</ul>

<h2>Quick Links</h2>
<p>⭐ Explore @AdvChatGptBot's full capabilities on Telegram: <a href="https://t.me/AdvChatGptBot" target="_blank">@AdvChatGptBot</a></p>
<p>⭐ Need Help? Check out our <a href="https://t.me/AdvChatGptBot/help" target="_blank">Help Menu</a>.</p>

<div style="text-align:center;">
    <button class="button">Start Chatting</button>
    <button class="button">Explore Features</button>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('</div>', unsafe_allow_html=True)

advAiBot.run()