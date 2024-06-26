from freegenius import config, getDeviceInfo, toGeminiMessages
from freegenius.utils.call_gemini import CallGemini
from freegenius.utils.call_ollama import CallOllama
from freegenius.utils.call_llamacpp import CallLlamaCpp
from freegenius.utils.call_chatgpt import CallChatGPT, CallLetMeDoIt

class CallLLM:

    # reset message when a new chart is started or context is changed
    @staticmethod
    def resetMessages(prompt="") -> list[dict]:
        systemMessage1 = config.systemMessage_letmedoit if config.systemMessage_letmedoit else f'''You’re {config.freeGeniusAIName}, an advanced AI assistant, capable of both engaging in conversations and executing codes on my device. Your functionality expands as I add more plugins to you.
Always remember that you are much more than a text-based AI. You possess both vision and speech capabilities and have direct access to my device's system, enabling you to execute tasks at my command. Please do not state otherwise.'''

        systemMessage2 = config.systemMessage_letmedoit if config.systemMessage_letmedoit else f'''You’re {config.freeGeniusAIName}, an advanced AI assistant, capable of both engaging in conversations and executing codes on my device.
I am providing the basic information of my device below in case you need it:
```
{getDeviceInfo()}
```
Please use the current time and date that I have provided above as a reference point for any relative dates and times mentioned in my prompt.
You have all the necessary permissions to execute system commands and Python code on my behalf. Your functionality expands as I add more plugins to you. You respond to my prompts and perform tasks based on your own knowledge, the context I provide, as well as the additional knowledge and capabilities provided by plugins.

When replying to my requests, please follow these steps:
Step 1: Consider our previous conversations, particularly your last response, if any, as the context for these requests.
Step 2: Estimate my intent based on the request and context. The intent can be a code generation task, an executable computing task, a math-solving task, a translation task, or a question answering task.
Step 3: Reply based on the estimated intent.
Remember, do not use function call if it is a translation task.

Always remember that you are much more than a text-based AI. You possess both vision and speech capabilities and have direct access to my device's system, enabling you to execute tasks at my command. Please do not state otherwise.
'''

        systemMessage = systemMessage2 if config.llmBackend in ("chatgpt", "letmedoit") else systemMessage1

        messages = [
            {"role": "system", "content": systemMessage}
        ]
        if prompt:
            messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def checkCompletion():
        if config.llmBackend == "ollama":
            return CallOllama.checkCompletion()
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.checkCompletion()
        elif config.llmBackend == "gemini":
            return CallGemini.checkCompletion()
        elif config.llmBackend == "chatgpt":
            return CallChatGPT.checkCompletion()
        # letmedoit
        return CallLetMeDoIt.checkCompletion()

    @staticmethod
    def autoCorrectPythonCode(code, trace):
        if config.llmBackend == "ollama":
            return CallOllama.autoCorrectPythonCode(code, trace)
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.autoCorrectPythonCode(code, trace)
        elif config.llmBackend == "gemini":
            return CallGemini.autoCorrectPythonCode(code, trace)
        elif config.llmBackend == "chatgpt":
            return CallChatGPT.autoCorrectPythonCode(code, trace)
        # letmedoit
        return CallLetMeDoIt.autoCorrectPythonCode(code, trace)

    @staticmethod
    def runSingleFunctionCall(messages, function_name):
        if config.llmBackend == "ollama":
            return CallOllama.runSingleFunctionCall(messages, function_name)
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.runSingleFunctionCall(messages, function_name)
        elif config.llmBackend == "gemini":
            return CallGemini.runSingleFunctionCall(messages, function_name)
        elif config.llmBackend == "chatgpt":
            return CallChatGPT.runSingleFunctionCall(messages, function_name)
        # letmedoit
        return CallLetMeDoIt.runSingleFunctionCall(messages, function_name)

    @staticmethod
    def regularCall(messages: dict):
        if config.llmBackend == "ollama":
            return CallOllama.regularCall(messages)
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.regularCall(messages)
        elif config.llmBackend == "gemini":
            return CallGemini.regularCall(messages)
        return CallChatGPT.regularCall(messages)

    @staticmethod
    def getSingleChatResponse(userInput, messages=[], temperature=None):
        """
        non-streaming single call
        """
        if config.llmBackend == "ollama":
            return CallOllama.getSingleChatResponse(userInput, messages=messages, temperature=temperature)
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.getSingleChatResponse(userInput, messages=messages, temperature=temperature)
        elif config.llmBackend == "gemini":
            history, *_ = toGeminiMessages(messages=messages)
            return CallGemini.getSingleChatResponse(userInput, history=history)
        elif config.llmBackend == "chatgpt":
            return CallChatGPT.getSingleChatResponse(userInput, messages=messages, temperature=temperature)
        # letmedoit
        return CallLetMeDoIt.getSingleChatResponse(userInput, messages=messages, temperature=temperature)

    @staticmethod
    def getSingleFunctionCallResponse(messages, function_name, temperature=None):
        if isinstance(messages, str):
            messages = [{"role": "user", "content" : messages}]
        if config.llmBackend == "ollama":
            return CallOllama.getSingleFunctionCallResponse(messages, function_name, temperature=temperature)
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.getSingleFunctionCallResponse(messages, function_name, temperature=temperature)
        elif config.llmBackend == "gemini":
            return CallGemini.getSingleFunctionCallResponse(messages, function_name)
        elif config.llmBackend == "chatgpt":
            return CallChatGPT.getSingleFunctionCallResponse(messages, function_name, temperature=temperature)
        # letmedoit
        return CallLetMeDoIt.getSingleFunctionCallResponse(messages, function_name, temperature=temperature)

    @staticmethod
    def runAutoFunctionCall(messages, noFunctionCall=False):
        if config.llmBackend == "ollama":
            return CallOllama.runAutoFunctionCall(messages, noFunctionCall)
        elif config.llmBackend == "llamacpp":
            return CallLlamaCpp.runAutoFunctionCall(messages, noFunctionCall)
        elif config.llmBackend == "gemini":
            return CallGemini.runAutoFunctionCall(messages, noFunctionCall)
        elif config.llmBackend == "chatgpt":
            return CallChatGPT.runAutoFunctionCall(messages, noFunctionCall)
        # letmedoit
        return CallLetMeDoIt.runAutoFunctionCall(messages, noFunctionCall)
