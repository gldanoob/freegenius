"""
FreeGenius AI Plugin - analyze images

analyze images

Backend: llamacpp, ollama
Model: llava <- customizable
To customise:
Change in config.py:
llamacppVisionModel_model_path
llamacppVisionModel_clip_model_path
ollamaVisionModel

Backend: gemini
Model: Gemini Pro Vision

Backend: chaptgpt, letmedoit
Model "gpt-4-vision-preview"
Reference: https://platform.openai.com/docs/guides/vision

[FUNCTION_CALL]
"""

from freegenius import config, print1, print2, is_valid_image_file, is_valid_image_url, startLlamacppVisionServer, stopLlamacppVisionServer
from freegenius.utils.shared_utils import SharedUtil
from freegenius.utils.call_chatgpt import check_openai_errors
import os
from openai import OpenAI
from freegenius.geminiprovision import GeminiProVision
from freegenius.utils.call_ollama import CallOllama

@check_openai_errors
def analyze_images(function_args):
    from freegenius import config

    if config.llmBackend == "gemini":
        answer = GeminiProVision(temperature=config.llmTemperature).analyze_images(function_args)
        if answer:
            config.tempContent = answer
            return ""
        else:
            return "[INVALID]"
    elif config.llmBackend in ("chatgpt", "letmedoit") and not config.openaiApiKey:
        return "OpenAI API key not found!"

    query = function_args.get("query") # required
    files = function_args.get("image_filepath") # required
    #print(files)
    if isinstance(files, str):
        if not files.startswith("["):
            files = f'["{files}"]'
        files = eval(files)

    filesCopy = files[:]
    for item in filesCopy:
        if os.path.isdir(item):
            for root, _, allfiles in os.walk(item):
                for file in allfiles:
                    file_path = os.path.join(root, file)
                    files.append(file_path)
            files.remove(item)

    content = []
    # valid image paths
    for i in files:
        if SharedUtil.is_valid_url(i) and is_valid_image_url(i):
            content.append({"type": "image_url", "image_url": {"url": i,},})
        elif os.path.isfile(i) and is_valid_image_file(i):
            content.append({"type": "image_url", "image_url": SharedUtil.encode_image(i),})
        else:
            files.remove(i)

    if content:
        if config.llmBackend in ("chatgpt", "letmedoit"):
            client = OpenAI()
        elif config.llmBackend == "llamacpp":
            # start llama.cpp vision server
            startLlamacppVisionServer()
            client = OpenAI(base_url=f"http://localhost:{config.llamacppServer_port}/v1", api_key="freegenius")
        elif config.llmBackend == "ollama":
            config.currentMessages[-1] = {'role': 'user', 'content': query, 'images': files}
            answer = CallOllama.getSingleChatResponse("", config.currentMessages, model=config.ollamaVisionModel)
            config.tempContent = answer
            print2("```assistant")
            print1(answer)
            print2("```")
            return ""

        content.insert(0, {"type": "text", "text": query,})

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                "role": "user",
                "content": content,
                }
            ],
            max_tokens=4096,
        )
        answer = response.choices[0].message.content
        config.tempContent = answer

        # display answer
        print2("```assistant")
        print1(answer)
        print2("```")

        # stop llama.cpp vision server
        if config.llmBackend == "llamacpp":
            stopLlamacppVisionServer()

        return ""
    return "[INVALID]"

functionSignature = {
    "examples": [
        "describe image",
        "compare images",
        "analyze image",
    ],
    "name": "analyze_images",
    "description": "describe or compare images",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Questions or requests that users ask about the given images",
            },
            "image_filepath": {
                "type": "string",
                "description": """Return a list of image paths or urls, e.g. '["image1.png", "/tmp/image2.png", "https://letmedoit.ai/image.png"]'. Return '[]' if image path is not provided.""",
            },
        },
        "required": ["query", "image_filepath"],
    },
}

config.addFunctionCall(signature=functionSignature, method=analyze_images)
config.inputSuggestions.append("Describe this image in detail: ")
config.inputSuggestions.append("Extract text from this image: ")