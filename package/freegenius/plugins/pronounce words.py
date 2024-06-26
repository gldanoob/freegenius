"""
FreeGenius AI Plugin - pronunce words

pronunce words

[FUNCTION_CALL]
"""

try:
    from gtts import gTTS
except:
    from freegenius import installPipPackage, print1
    installPipPackage(f"--upgrade gTTS")

from freegenius import config
from freegenius.utils.tts_utils import TTSUtil


from gtts import gTTS

def pronunce_words(function_args):
    words = function_args.get("words") # required
    language = function_args.get("language") # required
    print1("Loading speech feature ...")
    TTSUtil.play(words, language)
    return "Finished! Speech engine closed!"

functionSignature = {
    "examples": [
        "pronounce words",
        "speak in",
        "read",
    ],
    "name": "pronunce_words",
    "description": "pronounce words or sentences",
    "parameters": {
        "type": "object",
        "properties": {
            "words": {
                "type": "string",
                "description": "Words to be pronounced",
            },
            "language": {
                "type": "string",
                "description": "Language of the words",
                "enum": config.ttsLanguages,
            },
        },
        "required": ["words", "language"],
    },
}

config.addFunctionCall(signature=functionSignature, method=pronunce_words)
config.inputSuggestions.append("pronunce ")
