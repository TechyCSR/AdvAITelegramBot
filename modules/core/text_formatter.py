"""
Text formatting utilities for Telegram bot
Handles conversion between markdown and HTML for proper Telegram display
"""

import re
import html

def markdown_to_html(text: str) -> str:
    """
    Convert markdown formatting to Telegram-compatible HTML.
    Handles: code blocks, inline code, bold, italic, strikethrough, headers, links
    
    Args:
        text: Text with markdown formatting
        
    Returns:
        Text converted to HTML format compatible with Telegram
    """
    if not text or not isinstance(text, str):
        return text or ""
    
    # First, protect code blocks (triple backticks) by replacing with placeholders
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"
    
    text = re.sub(r'```[\s\S]*?```', save_code_block, text)
    
    # Protect inline code (single backticks)
    inline_codes = []
    def save_inline_code(match):
        inline_codes.append(match.group(0))
        return f"__INLINE_CODE_{len(inline_codes) - 1}__"
    
    text = re.sub(r'`[^`]+`', save_inline_code, text)
    
    # Escape HTML special characters in the main text
    text = html.escape(text)
    
    # Convert headers (### Header -> <b>Header</b>)
    text = re.sub(r'^#{1,6}\s*(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    
    # Convert bold (**text** or __text__ -> <b>text</b>)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Convert italic (*text* or _text_ -> <i>text</i>) - be careful not to match bold
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', text)
    
    # Convert strikethrough (~~text~~ -> <s>text</s>)
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    
    # Convert links [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Restore inline code
    for i, code in enumerate(inline_codes):
        # Extract just the code (remove backticks)
        code_content = code[1:-1]
        text = text.replace(f"__INLINE_CODE_{i}__", f"<code>{html.escape(code_content)}</code>")
    
    # Restore code blocks
    for i, block in enumerate(code_blocks):
        # Extract the code (remove triple backticks and optional language)
        match = re.match(r'```(?:\w+)?\n?([\s\S]*?)```', block)
        if match:
            code_content = match.group(1).strip()
        else:
            code_content = block[3:-3].strip()
        text = text.replace(f"__CODE_BLOCK_{i}__", f"<pre><code>{html.escape(code_content)}</code></pre>")
    
    return text


def strip_markdown(text: str) -> str:
    """
    Remove markdown formatting, leaving plain text.
    Useful for contexts where formatting isn't supported.
    
    Args:
        text: Text with markdown formatting
        
    Returns:
        Plain text without markdown
    """
    if not text or not isinstance(text, str):
        return text or ""
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0)[3:-3].strip(), text)
    
    # Remove inline code backticks
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove headers
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # Remove italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # Remove strikethrough
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    
    # Convert links to plain text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    return text


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for safe display.
    
    Args:
        text: Raw text that may contain HTML characters
        
    Returns:
        Escaped text safe for HTML display
    """
    return html.escape(text) if text else ""


def format_bold(text: str) -> str:
    """Return text wrapped in HTML bold tags"""
    return f"<b>{escape_html(text)}</b>"


def format_italic(text: str) -> str:
    """Return text wrapped in HTML italic tags"""
    return f"<i>{escape_html(text)}</i>"


def format_code(text: str) -> str:
    """Return text wrapped in HTML code tags"""
    return f"<code>{escape_html(text)}</code>"


def format_pre(text: str) -> str:
    """Return text wrapped in HTML pre tags"""
    return f"<pre>{escape_html(text)}</pre>"
