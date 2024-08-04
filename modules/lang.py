
from googletrans import Translator



global default_lang
default_lang = 'en'




def translate_to_lang(text,lang=None):
    if lang is None:
        lang = default_lang
    translator = Translator()
    translation = translator.translate(text, src='en', dest=lang)
    return translation.text


# while True:
#     print(translate_to_lang("Hello, How are you?"))
#     break