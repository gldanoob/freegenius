import os, sys, platform

# check python version
# requires python 3.8+; required by package 'tiktoken'
pythonVersion = sys.version_info
if pythonVersion < (3, 8):
    print("Python version higher than 3.8 is required!")
    print("Closing ...")
    exit(1)
elif pythonVersion >= (3, 12):
    print("Some features may not work with python version newer than 3.11!")

# check package path
thisFile = os.path.realpath(__file__)
packageFolder = os.path.dirname(thisFile)
package = os.path.basename(packageFolder)

# set current directory
if os.getcwd() != packageFolder:
    os.chdir(packageFolder)

# create conifg.py in case it is deleted due to errors
configFile = os.path.join(packageFolder, "config.py")
if not os.path.isfile(configFile):
    open(configFile, "a", encoding="utf-8").close()

# import config module
from freegenius import config

# import other libraries

import os, geocoder, platform, socket, geocoder, datetime, requests, netifaces, getpass, pendulum, pkg_resources
import traceback, uuid, re, textwrap, glob, wcwidth, shutil, threading, time, tiktoken, subprocess, json
from packaging import version
from chromadb.utils import embedding_functions
from pygments.styles import get_style_by_name
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit import prompt
from typing import Optional, Any
from vertexai.preview.generative_models import Content, Part
from pathlib import Path
from PIL import Image
from openai import OpenAI
from freegenius.utils.terminal_mode_dialogs import TerminalModeDialogs

# a dummy import line to resolve ALSA error display on Linux
import sounddevice

# tool selection

def selectTool(search_result, closest_distance) -> Optional[int]:
    if closest_distance <= config.tool_auto_selection_threshold:
        # auto
        return 0
    else:
        # manual
        tool_options = []
        tool_descriptions = []
        for index, item in enumerate(search_result["metadatas"][0]):
            tool_options.append(str(index))
            tool_descriptions.append(item["name"].replace("_", " "))
        stopSpinning()
        tool = TerminalModeDialogs(None).getValidOptions(
            title="Tool Selection",
            text="Select a tool:",
            options=tool_options,
            descriptions=tool_descriptions,
            default=tool_options[0],
        )
        if tool:
            return int(tool)
    return None

# files

def fileNamesWithoutExtension(dir, ext):
    # Note: pathlib.Path(file).stem does not work with file name containg more than one dot, e.g. "*.db.sqlite"
    files = glob.glob(os.path.join(dir, "*.{0}".format(ext)))
    return sorted([file[len(dir)+1:-(len(ext)+1)] for file in files if os.path.isfile(file)])

def getLocalStorage():
    # config.freeGeniusAIName
    if not hasattr(config, "freeGeniusAIName") or not config.freeGeniusAIName:
        config.freeGeniusAIName = "FreeGenius AI"

    # option 1: config.storagedirectory; user custom folder
    if not hasattr(config, "storagedirectory") or (config.storagedirectory and not os.path.isdir(config.storagedirectory)):
        config.storagedirectory = ""
    if config.storagedirectory:
        return config.storagedirectory
    # option 2: defaultStorageDir; located in user home directory
    defaultStorageDir = os.path.join(os.path.expanduser('~'), config.freeGeniusAIName.split()[0].lower())
    try:
        Path(defaultStorageDir).mkdir(parents=True, exist_ok=True)
    except:
        pass
    if os.path.isdir(defaultStorageDir):
        return defaultStorageDir
    # option 3: directory "files" in app directory; to be deleted on every upgrade
    else:
        return os.path.join(packageFolder, "files")

# image

def is_valid_image_url(url): 
    try: 
        response = requests.head(url, timeout=30)
        content_type = response.headers['content-type'] 
        if 'image' in content_type: 
            return True 
        else: 
            return False 
    except requests.exceptions.RequestException: 
        return False

def is_valid_image_file(file_path):
    try:
        # Open the image file
        with Image.open(file_path) as img:
            # Check if the file format is supported by PIL
            img.verify()
            return True
    except (IOError, SyntaxError) as e:
        # The file path is not a valid image file path
        return False

# call llm

def executeToolFunction(func_arguments: dict, function_name: str):
    def notifyDeveloper(func_name):
        if config.developer:
            #print1(f"running function '{func_name}' ...")
            print_formatted_text(HTML(f"<{config.terminalPromptIndicatorColor2}>Running function</{config.terminalPromptIndicatorColor2}> <{config.terminalCommandEntryColor2}>'{func_name}'</{config.terminalCommandEntryColor2}> <{config.terminalPromptIndicatorColor2}>...</{config.terminalPromptIndicatorColor2}>"))
    if not function_name in config.toolFunctionMethods:
        if config.developer:
            print1(f"Unexpected function: {function_name}")
            print1(config.divider)
            print(func_arguments)
            print1(config.divider)
        function_response = "[INVALID]"
    else:
        notifyDeveloper(function_name)
        function_response = config.toolFunctionMethods[function_name](func_arguments)
    return function_response

def toParameterSchema(schema) -> dict:
    """
    extract parameter schema from full schema
    """
    if "parameters" in schema:
        return schema["parameters"]
    return schema

def toGeminiMessages(messages: dict=[]) -> Optional[list]:
    systemMessage = ""
    lastUserMessage = ""
    if messages:
        history = []
        for i in config.currentMessages:
            role = i.get("role", "")
            content = i.get("content", "")
            if role in ("user", "assistant"):
                history.append(Content(role="user" if role == "user" else "model", parts=[Part.from_text(content)]))
                if role == "user":
                    lastUserMessage = content
            elif role == "system":
                systemMessage = content
        if history and history[-1].role == "user":
            history = history[:-1]
        else:
            lastUserMessage = ""
        if not history:
            history = None
    else:
        history = None
    return history, systemMessage, lastUserMessage

# python code

def execPythonFile(script="", content=""):
    if script or content:
        try:
            def runCode(text):
                code = compile(text, script, 'exec')
                exec(code, globals())
            if content:
                runCode(content)
            else:
                with open(script, 'r', encoding='utf8') as f:
                    runCode(f.read())
            return True
        except:
            print1("Failed to run '{0}'!".format(os.path.basename(script)))
            showErrors()
    return False

def isValidPythodCode(code):
    try:
        codeObject = compile(code, '<string>', 'exec')
        return codeObject
    except:
        return None

def extractPythonCode(content):
    if code_only := re.search('```python\n(.+?)```', content, re.DOTALL):
        content = code_only.group(1)
    return content if isValidPythodCode(content) is not None else ""

def fineTunePythonCode(code):
    # dedent
    code = textwrap.dedent(code).rstrip()
    # capture print output
    config.pythonFunctionResponse = ""
    insert_string = "from freegenius import config\nconfig.pythonFunctionResponse = "
    code = re.sub("^!(.*?)$", r'import os\nos.system(""" \1 """)', code, flags=re.M)
    if "\n" in code:
        substrings = code.rsplit("\n", 1)
        lastLine = re.sub("print\((.*)\)", r"\1", substrings[-1])
        if lastLine.startswith(" "):
            lastLine = re.sub("^([ ]+?)([^ ].*?)$", r"\1config.pythonFunctionResponse = \2", lastLine)
            code = f"from freegenius import config\n{substrings[0]}\n{lastLine}"
        else:
            lastLine = f"{insert_string}{lastLine}"
            code = f"{substrings[0]}\n{lastLine}"
    else:
        code = f"{insert_string}{code}"
    return code

def getPythonFunctionResponse(code):
    #return str(config.pythonFunctionResponse) if config.pythonFunctionResponse is not None and (type(config.pythonFunctionResponse) in (int, float, str, list, tuple, dict, set, bool) or str(type(config.pythonFunctionResponse)).startswith("<class 'numpy.")) and not ("os.system(" in code) else ""
    return "" if config.pythonFunctionResponse is None else str(config.pythonFunctionResponse)

def showRisk(risk):
    if not config.confirmExecution in ("always", "medium_risk_or_above", "high_risk_only", "none"):
        config.confirmExecution = "always"
    print1(f"[risk level: {risk}]")

def confirmExecution(risk):
    if config.confirmExecution == "always" or (risk == "high" and config.confirmExecution == "high_risk_only") or (not risk == "low" and config.confirmExecution == "medium_risk_or_above"):
        return True
    else:
        return False

# embedding

def getEmbeddingFunction(embeddingModel=None):
    # import statement is placed here to make this file compatible on Android
    embeddingModel = embeddingModel if embeddingModel is not None else config.embeddingModel
    if embeddingModel in ("text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"):
        return embedding_functions.OpenAIEmbeddingFunction(api_key=config.openaiApiKey, model_name=embeddingModel)
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embeddingModel) # support custom Sentence Transformer Embedding models by modifying config.embeddingModel

# chromadb

def get_or_create_collection(collection_name):
    collection = config.tool_store_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=getEmbeddingFunction(),
    )
    return collection

def add_vector(collection, text, metadata):
    id = str(uuid.uuid4())
    collection.add(
        documents = [text],
        metadatas = [metadata],
        ids = [id]
    )

def query_vectors(collection, query, n=1):
    return collection.query(
        query_texts=[query],
        n_results = n,
    )

# spinning

def spinning_animation(stop_event):
    while not stop_event.is_set():
        for symbol in "|/-\\":
            print(symbol, end="\r")
            time.sleep(0.1)

def startSpinning():
    config.stop_event = threading.Event()
    config.spinner_thread = threading.Thread(target=spinning_animation, args=(config.stop_event,))
    config.spinner_thread.start()

def stopSpinning():
    try:
        config.stop_event.set()
        config.spinner_thread.join()
    except:
        pass

# display information

def wrapText(content, terminal_width=None):
    if terminal_width is None:
        terminal_width = shutil.get_terminal_size().columns
    return "\n".join([textwrap.fill(line, width=terminal_width) for line in content.split("\n")])

def transformText(text):
    for transformer in config.outputTransformers:
            text = transformer(text)
    return text

def print1(content):
    content = transformText(content)
    if config.wrapWords:
        # wrap words to fit terminal width
        terminal_width = shutil.get_terminal_size().columns
        print(wrapText(content, terminal_width))
        # remarks: 'fold' or 'fmt' does not work on Windows
        # pydoc.pipepager(f"{content}\n", cmd=f"fold -s -w {terminal_width}")
        # pydoc.pipepager(f"{content}\n", cmd=f"fmt -w {terminal_width}")
    else:
        print(content)

def print2(content):
    print_formatted_text(HTML(f"<{config.terminalPromptIndicatorColor2}>{content}</{config.terminalPromptIndicatorColor2}>"))

def print3(content):
    splittedContent = content.split(": ", 1)
    if len(splittedContent) == 2:
        key, value = splittedContent
        print_formatted_text(HTML(f"<{config.terminalPromptIndicatorColor2}>{key}:</{config.terminalPromptIndicatorColor2}> {value}"))
    else:
        print2(splittedContent)

def getStringWidth(text):
    width = 0
    for character in text:
        width += wcwidth.wcwidth(character)
    return width

def getPygmentsStyle():
    theme = config.pygments_style if config.pygments_style else "stata-dark" if not config.terminalResourceLinkColor.startswith("ansibright") else "stata-light"
    return style_from_pygments_cls(get_style_by_name(theme))

def showErrors():
    trace = traceback.format_exc()
    print(trace if config.developer else "Error encountered!")
    return trace

# ip

def get_wan_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        data = response.json()
        return data['ip']
    except:
        return ""

def get_local_ip():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        addresses = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addresses:
            for address in addresses[netifaces.AF_INET]:
                ip = address['addr']
                if ip != '127.0.0.1':
                    return ip

# time

def getDayOfWeek():
    if config.isTermux:
        return ""
    else:
        now = pendulum.now() 
        return now.format('dddd')

# device information

def getDeviceInfo(includeIp=False):
    g = geocoder.ip('me')
    if hasattr(config, "thisPlatform"):
        thisPlatform = config.thisPlatform
    else:
        thisPlatform = platform.system()
        if thisPlatform == "Darwin":
            thisPlatform = "macOS"
    if config.includeIpInDeviceInfoTemp or includeIp or (config.includeIpInDeviceInfo and config.includeIpInDeviceInfoTemp):
        wan_ip = get_wan_ip()
        local_ip = get_local_ip()
        ipInfo = f'''Wan ip: {wan_ip}
Local ip: {local_ip}
'''
    else:
        ipInfo = ""
    if config.isTermux:
        dayOfWeek = ""
    else:
        dayOfWeek = getDayOfWeek()
        dayOfWeek = f"Current day of the week: {dayOfWeek}"
    return f"""Operating system: {thisPlatform}
Version: {platform.version()}
Machine: {platform.machine()}
Architecture: {platform.architecture()[0]}
Processor: {platform.processor()}
Hostname: {socket.gethostname()}
Username: {getpass.getuser()}
Python version: {platform.python_version()}
Python implementation: {platform.python_implementation()}
Current directory: {os.getcwd()}
Current time: {str(datetime.datetime.now())}
{dayOfWeek}
{ipInfo}Latitude & longitude: {g.latlng}
Country: {g.country}
State: {g.state}
City: {g.city}"""

# token management

# token limit
# reference: https://platform.openai.com/docs/models/gpt-4
tokenLimits = {
    "gpt-4-turbo-preview": 128000, # Returns a maximum of 4,096 output tokens.
    "gpt-4-0125-preview": 128000, # Returns a maximum of 4,096 output tokens.
    "gpt-4-1106-preview": 128000, # Returns a maximum of 4,096 output tokens.
    "gpt-3.5-turbo": 16385, # Returns a maximum of 4,096 output tokens.
    "gpt-3.5-turbo-16k": 16385,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
}

def getDynamicTokens(messages, functionSignatures=None):
    if functionSignatures is None:
        functionTokens = 0
    else:
        functionTokens = count_tokens_from_functions(functionSignatures)
    tokenLimit = tokenLimits[config.chatGPTApiModel]
    currentMessagesTokens = count_tokens_from_messages(messages) + functionTokens
    availableTokens = tokenLimit - currentMessagesTokens
    if availableTokens >= config.chatGPTApiMaxTokens:
        return config.chatGPTApiMaxTokens
    elif (config.chatGPTApiMaxTokens > availableTokens > config.chatGPTApiMinTokens):
        return availableTokens
    return config.chatGPTApiMinTokens

def count_tokens_from_functions(functionSignatures, model=""):
    count = 0
    if not model:
        model = config.chatGPTApiModel
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    for i in functionSignatures:
        count += len(encoding.encode(str(i)))
    return count

# The following method was modified from source:
# https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def count_tokens_from_messages(messages, model=""):
    if not model:
        model = config.chatGPTApiModel

    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-turbo-preview",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4",
            "gpt-4-0613",
            "gpt-4-32k",
            "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        #print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return count_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        #print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return count_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""count_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        if not "content" in message or not message.get("content", ""):
            num_tokens += len(encoding.encode(str(message)))
        else:
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

# API keys / credentials

def changeChatGPTAPIkey():
    print("Enter your OpenAI API Key [optional]:")
    apikey = prompt(default=config.openaiApiKey, is_password=True)
    if apikey and not apikey.strip().lower() in (config.cancel_entry, config.exit_entry):
        config.openaiApiKey = apikey
    else:
        config.openaiApiKey = "freegenius"
    setChatGPTAPIkey()

def setChatGPTAPIkey():
    # instantiate a client that can shared with plugins
    os.environ["OPENAI_API_KEY"] = config.openaiApiKey
    config.oai_client = OpenAI()
    # set variable 'OAI_CONFIG_LIST' to work with pyautogen
    oai_config_list = []
    for model in tokenLimits.keys():
        oai_config_list.append({"model": model, "api_key": config.openaiApiKey})
    os.environ["OAI_CONFIG_LIST"] = json.dumps(oai_config_list)

def setGoogleCredentials():
    config.google_cloud_credentials_file = os.path.join(storageDir, "credentials_google_cloud.json")
    if config.google_cloud_credentials and os.path.isfile(config.google_cloud_credentials):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_cloud_credentials
    else:
        gccfile2 = os.path.join(storageDir, "credentials_googleaistudio.json")
        gccfile3 = os.path.join(storageDir, "credentials_googletts.json")

        if os.path.isfile(config.google_cloud_credentials_file):
            config.google_cloud_credentials = config.google_cloud_credentials_file
        elif os.path.isfile(gccfile2):
            config.google_cloud_credentials = gccfile2
        elif os.path.isfile(gccfile3):
            config.google_cloud_credentials = gccfile3
        else:
            config.google_cloud_credentials = ""
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_cloud_credentials if config.google_cloud_credentials else ""

# package management

def isCommandInstalled(package):
    return True if shutil.which(package.split(" ", 1)[0]) else False

def getPackageInstalledVersion(package):
    try:
        installed_version = pkg_resources.get_distribution(package).version
        return version.parse(installed_version)
    except pkg_resources.DistributionNotFound:
        return None

def getPackageLatestVersion(package):
    try:
        response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=10)
        latest_version = response.json()['info']['version']
        return version.parse(latest_version)
    except:
        return None

def restartApp():
    print(f"Restarting {config.freeGeniusAIName} ...")
    os.system(f"{sys.executable} {config.freeGeniusAIFile}")
    exit(0)

def updateApp():
    thisPackage = f"{package}_android" if config.isTermux else package
    print(f"Checking '{thisPackage}' version ...")
    installed_version = getPackageInstalledVersion(thisPackage)
    if installed_version is None:
        print("Installed version information is not accessible!")
    else:
        print(f"Installed version: {installed_version}")
    latest_version = getPackageLatestVersion(thisPackage)
    if latest_version is None:
        print("Latest version information is not accessible at the moment!")
    elif installed_version is not None:
        print(f"Latest version: {latest_version}")
        if latest_version > installed_version:
            if thisPlatform == "Windows":
                print("Automatic upgrade feature is yet to be supported on Windows!")
                print(f"Run 'pip install --upgrade {thisPackage}' to manually upgrade this app!")
            else:
                try:
                    # upgrade package
                    installPipPackage(f"--upgrade {thisPackage}")
                    restartApp()
                except:
                    if config.developer:
                        print(traceback.format_exc())
                    print(f"Failed to upgrade '{thisPackage}'!")

def installPipPackage(module, update=True):
    #executablePath = os.path.dirname(sys.executable)
    #pippath = os.path.join(executablePath, "pip")
    #pip = pippath if os.path.isfile(pippath) else "pip"
    #pip3path = os.path.join(executablePath, "pip3")
    #pip3 = pip3path if os.path.isfile(pip3path) else "pip3"

    if isCommandInstalled("pip"):
        pipInstallCommand = f"{sys.executable} -m pip install"

        if update:
            from freegenius import config
            if not config.isPipUpdated:
                pipFailedUpdated = "pip tool failed to be updated!"
                try:
                    # Update pip tool in case it is too old
                    updatePip = subprocess.Popen(f"{pipInstallCommand} --upgrade pip", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    *_, stderr = updatePip.communicate()
                    if not stderr:
                        print("pip tool updated!")
                    else:
                        print(pipFailedUpdated)
                except:
                    print(pipFailedUpdated)
                config.isPipUpdated = True
        try:
            upgrade = (module.startswith("-U ") or module.startswith("--upgrade "))
            if upgrade:
                moduleName = re.sub("^[^ ]+? (.+?)$", r"\1", module)
            else:
                moduleName = module
            print(f"{'Upgrading' if upgrade else 'Installing'} '{moduleName}' ...")
            installNewModule = subprocess.Popen(f"{pipInstallCommand} {module}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            *_, stderr = installNewModule.communicate()
            if not stderr:
                print(f"Package '{moduleName}' {'upgraded' if upgrade else 'installed'}!")
            else:
                print(f"Failed {'upgrading' if upgrade else 'installing'} package '{moduleName}'!")
                if config.developer:
                    print(stderr)
            return True
        except:
            return False

    else:
        print("pip command is not found!")
        return False

# config

def setToolDependence(entry: Any) -> bool:
    try:
        entry = float(entry)
        if 0 <= entry <=1.0:
            config.tool_dependence = entry
            print3(f"Tool dependence changed to: {entry}")
            return True
    except:
        pass
    return False

##########

# set up shared configs

config.freeGeniusAIFolder = packageFolder
config.freeGeniusAIFile = os.path.join(config.freeGeniusAIFolder, "main.py")
if not hasattr(config, "freeGeniusAIName") or not config.freeGeniusAIName:
    config.freeGeniusAIName = "FreeGenius AI"

config.isTermux = True if os.path.isdir("/data/data/com.termux/files/home") else False

if not hasattr(config, "isPipUpdated"):
    config.isPipUpdated = False

config.stopSpinning = stopSpinning
config.localStorage = getLocalStorage()

from freegenius.utils.config_tools import *
config.loadConfig = loadConfig
config.setConfig = setConfig

from freegenius.utils.tool_plugins import Plugins
config.addFunctionCall = Plugins.addFunctionCall

from freegenius.utils.vlc_utils import VlcUtil
config.isVlcPlayerInstalled = VlcUtil.isVlcPlayerInstalled()

try:
    # hide pygame welcome message
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame
    pygame.mixer.init()
    config.isPygameInstalled = True
except:
    config.isPygameInstalled = False

thisPlatform = platform.system()
config.thisPlatform = "macOS" if thisPlatform == "Darwin" else thisPlatform
if config.terminalEnableTermuxAPI:
    config.open = "termux-share"
elif thisPlatform == "Linux":
    config.open = "xdg-open"
elif thisPlatform == "Darwin":
    config.open = "open"
elif thisPlatform == "Windows":
    config.open = "start"

config.excludeConfigList = []
config.includeIpInDeviceInfoTemp = config.includeIpInDeviceInfo
config.divider = "--------------------"
config.tts = False if not config.isVlcPlayerInstalled and not config.isPygameInstalled and not config.ttsCommand and not config.elevenlabsApi else True
config.outputTransformers = []

# save loaded configs
config.saveConfig()

# environment variables
os.environ["TOKENIZERS_PARALLELISM"] = config.tokenizers_parallelism

# create shortcuts
from freegenius.utils.shortcuts import createShortcuts
createShortcuts()

# setup optional credentials
setChatGPTAPIkey()
setGoogleCredentials()