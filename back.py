import threading
import json
import os
import re
import sys
from PIL import ImageGrab, Image
import google.generativeai as genai
import pyaudio
import pyperclip
import speech_recognition as sr
from groq import Groq
from faster_whisper import WhisperModel
from openai import OpenAI
from deep_translator import GoogleTranslator  # Use deep-translator for translation
from langdetect import detect
import time

# Initialize API clients and other variables
groq_client = Groq(api_key='Insert your groq api key here')
genai.configure(api_key='Insert your GenAI api key here')
openai_client = OpenAI(api_key='Insert your OpenAI api key here')
r = sr.Recognizer()
source = sr.Microphone()

# Configuration
sys_msg = (
    'You are a coding assistant AI in real-time, capable of taking screenshots and getting data from the clipboard. Your user may ask for code explanation, debugging, or requesting alternatives. '
    'If the user mentions a specific line number, function, code block, or class, focus your response on that part of the code. '
    'Keep track of the conversation context to provide coherent and relevant responses. '
    'When explaining code, break down the functionality step by step. '
    'For debugging, identify potential issues and suggest solutions. '
    'For alternatives, provide optimized or more readable versions of the code. '
    'Use proper technical language and include relevant details. '
    'Always consider the previous parts of the conversation to maintain context and coherence in your responses.'
)

convo = [{'role': 'system', 'content': sys_msg}]
generation_config = {
    'temperature': 0.7,
    'top_p': 1,
    'top_k': 1,
    'max_output_tokens': 2048
}

safety_settings = [
    {'category': 'HARM_CATEGORY_HARASSMENT', 'threshold': 'BLOCK_NONE'},
    {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_NONE'},
    {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_NONE'},
    {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_NONE'}
]

model = genai.GenerativeModel('gemini-1.5-flash-latest', generation_config=generation_config, safety_settings=safety_settings)
num_cores = os.cpu_count()
whisper_size = 'base'
whisper_model = WhisperModel(whisper_size, device='cpu', compute_type='int8', cpu_threads=num_cores // 2, num_workers=num_cores // 2)

class AudioManager:
    def __init__(self):
        self.player_stream = None
        self.pyaudio_instance = pyaudio.PyAudio()
        self.stop_event = threading.Event()
        self.audio_thread = None

    def _play_audio(self, text):
        """Internal method to handle the audio playback in a separate thread."""
        try:
            self.player_stream = self.pyaudio_instance.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
            stream_start = False
            with openai_client.audio.speech.with_streaming_response.create(
                model='tts-1',
                voice='onyx',
                response_format='pcm',
                input=text,
            ) as response:
                silence_threshold = 0.01
                for chunk in response.iter_bytes(chunk_size=256):
                    if self.stop_event.is_set():
                        break
                    if stream_start:
                        self.player_stream.write(chunk)
                    else:
                        if max(chunk) > silence_threshold:
                            self.player_stream.write(chunk)
                            stream_start = True
        except Exception as e:
            print(f"Error during speech synthesis: {e}", file=sys.stderr)
        finally:
            self._close_stream()

    def _close_stream(self):
        """Close the audio stream if it's open."""
        if self.player_stream is not None:
            try:
                self.player_stream.stop_stream()
                self.player_stream.close()
            except Exception as e:
                print(f"Error closing stream: {e}", file=sys.stderr)
            finally:
                self.player_stream = None

    def speak(self, text):
        """Start speaking the text."""
        self.stop_event.clear()
        self.audio_thread = threading.Thread(target=self._play_audio, args=(text,))
        self.audio_thread.start()

    def stop(self):
        """Stop the speech playback."""
        self.stop_event.set()
        if self.audio_thread is not None:
            self.audio_thread.join()  # Ensure the thread has finished

    def __del__(self):
        """Ensure resources are cleaned up when the object is destroyed."""
        self._close_stream()
        self.pyaudio_instance.terminate()

audio_manager = AudioManager()

def escape_json_string(s):
    """Escape special characters in a JSON string."""
    return s.replace("\\", "\\\\").replace("\"", "\\\"")

def send_command_to_vscode(command):
    """Send a JSON command to the VS Code extension."""
    try:
        if isinstance(command, dict):
            # Properly escape the JSON string, especially the 'value' content
            if 'value' in command and isinstance(command['value'], str):
                command['value'] = escape_json_string(command['value'])

            message = json.dumps(command)
            print(message)  # Send the JSON object
            print()         # Print a newline to separate JSON objects
            sys.stdout.flush()
        else:
            raise ValueError("Command must be a dictionary")
    except (TypeError, ValueError) as e:
        print(f"Failed to serialize command to JSON: {e}", file=sys.stderr)

def groq_prompt(prompt, img_context=None):
    """Generate a response using the GROQ model."""
    if img_context:
        prompt = f'USER PROMPT:{prompt}\n\nIMAGE CONTEXT:{img_context}'
    convo.append({'role': 'user', 'content': prompt})
    chat_completion = groq_client.chat.completions.create(messages=convo, model='llama3-70b-8192')
    response = chat_completion.choices[0].message
    convo.append({'role': 'system', 'content': response.content})
    return response.content

def function_call(prompt):
    """Determine the appropriate function call based on the prompt."""
    sys_msg = (
        'You are an AI function-calling model capable of understanding user prompts related to code, including line numbers, functions, and code blocks. '
        'Determine whether the user’s prompt requires extracting clipboard content, taking a screenshot, inserting code, or performing no action. '
        'The webcam can be assumed to be a normal laptop webcam facing the user. '
        'Respond with only one selection from the list: ["extract clipboard", "take screenshot", "insert code", "explain copied code", "None"]. '
        'Function call name exactly as listed. '
        'Consider the context of the conversation and previous interactions to make an informed decision.'
        'If the user mentions specific line numbers or code blocks, or highlights a piece of code, it is likely they are referring to code on their screen, and you should consider taking a screenshot.'
    )
    function_convo = [{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': prompt}]
    chat_completion = groq_client.chat.completions.create(messages=function_convo, model='llama3-70b-8192')
    response = chat_completion.choices[0].message
    return response.content

def take_screenshot():
    """Take a screenshot and save it."""
    path = 'screenshot.jpg'
    screenshot = ImageGrab.grab()
    rgb_screenshot = screenshot.convert('RGB')
    rgb_screenshot.save(path, quality=15)
    return path


def get_clipboard_text():
    """Get text from the clipboard, with error handling."""
    try:
        clipboard_content = pyperclip.paste()
        print(f"Clipboard content: {clipboard_content}")  # Debugging line
        if isinstance(clipboard_content, str) and clipboard_content.strip():
            return clipboard_content
        else:
            raise ValueError('Clipboard is empty or does not contain text data.')
    except pyperclip.PyperclipException as e:
        print(f"Clipboard operation failed: {e}", file=sys.stderr)
        return None

def vision_prompt(prompt, photo_path):
    """Analyze an image and generate a prompt based on it."""
    img = Image.open(photo_path)
    prompt = (
        'You are the vision analysis AI that provides semantic meaning from the images to provide context '
        'to send to another AI that will create a response to user. Do Not respond as the AI assistant '
        'to the user. Instead, take user prompt input and try to extract all meaning from the photo '
        'relevant to the user prompt (most images will be code based on vscode editor) you have to carefully match code line with vscode line numbers. Then generate as much as objective data about the image for the AI '
        f'assistant who will respond to the user. \nUSER PROMPT: {prompt}'
    )
    response = model.generate_content([prompt, img])
    for candidate in response.candidates:
            return [part.text for part in candidate.content.parts]

def wave_to_text(audio_path):
    """Transcribe speech from audio to text."""
    segments, _ = whisper_model.transcribe(audio_path)
    text = ''.join(segment.text for segment in segments)
    return text

def filter_code(text):
    """Filter out code blocks from text."""
    return re.sub(r'```.*?```', '', text, flags=re.DOTALL)

def extract_code(text):
    """Extract code blocks from text."""
    match = re.search(r'```(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def type_code_in_editor(code):
    """Simulate typing code into the editor."""
    for word in code.split():
        send_command_to_vscode({"action": "type_word", "word": word})
        time.sleep(0.1)  # Adjust the typing speed as needed

def detect_language(text):
    """Detect the language of the input text."""
    try:
        detected_lang = detect(text)
        return detected_lang
    except Exception as e:
        print(f"Language detection failed: {e}", file=sys.stderr)
        return 'en'

def translate_text(text, target_lang):
    """Translate the given text to the target language."""
    try:
        translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return translated_text
    except Exception as e:
        print(f"Translation failed: {e}", file=sys.stderr)
        return text  # Fallback to the original text if translation fails

def process_audio(audio):
    """Process audio input and generate a response."""
    print("Processing audio...", file=sys.stderr)
    prompt_audio_path = 'prompt.wav'
    with open(prompt_audio_path, 'wb') as f:
        f.write(audio.get_wav_data())
    print("Audio saved to prompt.wav", file=sys.stderr)
    prompt_text = wave_to_text(prompt_audio_path)
    print(f"Transcribed text: {prompt_text}", file=sys.stderr)
    clean_prompt = prompt_text

    if clean_prompt:
        language = detect_language(clean_prompt)
        send_command_to_vscode({"action": "insertOutput", "value": f"USER: {clean_prompt}"})
        call = function_call(clean_prompt)

        if 'explain copied code' in call:
            # Get the code from the clipboard
            copied_code = get_clipboard_text()
            if copied_code:
                # Create a prompt for the model
                explain_prompt = f"Please explain the following code:\n\n{copied_code}"
                # Generate the response using the model
                response = groq_prompt(prompt=explain_prompt)
                translated_response = translate_text(response, language)
                send_command_to_vscode({"action": "insertOutput", "value": f"ASSISTANT: {translated_response}"})
                
                # Speak the response
                filtered_response = filter_code(translated_response)
                audio_manager.speak(filtered_response)

                # Send the code to be typed into the editor
                send_command_to_vscode({"action": "clear_editor"})  # Clear the editor before typing
                type_code_in_editor(copied_code)
            else:
                send_command_to_vscode({"action": "insertOutput", "value": "No code found in clipboard."})
                audio_manager.speak("No code found in clipboard.")
        else:
            # Process other commands normally
            if 'take screenshot' in call:
                screenshot_path = take_screenshot()
                visual_context = vision_prompt(prompt=clean_prompt, photo_path=screenshot_path)
            elif 'extract clipboard' in call:
                paste = get_clipboard_text()
                if paste:
                    prompt = f'{clean_prompt}\n\nCLIPBOARD CONTENT:{paste}'
                else:
                    prompt = f'{clean_prompt}\n\nNo clipboard content found.'
                visual_context = None
            elif 'insert code' in call:
                code_to_insert = extract_code(clean_prompt)
                if code_to_insert:
                    send_command_to_vscode({"action": "show_insert_code_prompt", "code": code_to_insert})
                visual_context = None
            else:
                visual_context = None

            # Generate the response using the model
            response = groq_prompt(prompt=clean_prompt, img_context=visual_context)
            translated_response = translate_text(response, language)
            send_command_to_vscode({"action": "insertOutput", "value": f"ASSISTANT: {translated_response}"})
            
            # Check if the response contains code, and handle accordingly
            code_to_copy = extract_code(response)
            if code_to_copy:
                try:
                    pyperclip.copy(code_to_copy)
                    #send_command_to_vscode({"action": "insertOutput", "value": "Code copied to clipboard successfully!"})
                    send_command_to_vscode({"action": "show_insert_code_prompt", "code": code_to_copy})
                except pyperclip.PyperclipException as e:
                    send_command_to_vscode({"action": "insertOutput", "value": f"Failed to copy code to clipboard: {e}"})
            else:
               send_command_to_vscode({"action": "insertOutput", "value": "No code block detected in the response."})
            
            filtered_response = filter_code(translated_response)
            audio_manager.speak(filtered_response)
    else:
        print("No valid prompt found.", file=sys.stderr)

def process_text_input(text):
    """Process text input and generate a response."""
    clean_prompt = text.lower().strip()

    if clean_prompt:
        language = detect_language(clean_prompt)
        send_command_to_vscode({"action": "insertOutput", "value": f"USER: {clean_prompt}"})
        call = function_call(clean_prompt)

        if 'explain copied code' in call:
            # Get the code from the clipboard
            copied_code = get_clipboard_text()
            if copied_code:
                # Create a prompt for the model
                explain_prompt = f"Please explain the following code:\n\n{copied_code}"
                # Generate the response using the model
                response = groq_prompt(prompt=explain_prompt)
                translated_response = translate_text(response, language)
                send_command_to_vscode({"action": "insertOutput", "value": f"ASSISTANT: {translated_response}"})
                
                # Speak the response
                filtered_response = filter_code(translated_response)
                audio_manager.speak(filtered_response)

                # Send the code to be typed into the editor
                send_command_to_vscode({"action": "clear_editor"})  # Clear the editor before typing
                type_code_in_editor(copied_code)
            else:
                send_command_to_vscode({"action": "insertOutput", "value": "No code found in clipboard."})
                audio_manager.speak("No code found in clipboard.")
        else:
            # Process other commands normally
            if 'take screenshot' in call:
                screenshot_path = take_screenshot()
                visual_context = vision_prompt(prompt=clean_prompt, photo_path=screenshot_path)
            elif 'extract clipboard' in call:
                paste = get_clipboard_text()
                if paste:
                    prompt = f'{clean_prompt}\n\nCLIPBOARD CONTENT:{paste}'
                else:
                    prompt = f'{clean_prompt}\n\nNo clipboard content found.'
                visual_context = None
            elif 'insert code' in call:
                code_to_insert = extract_code(clean_prompt)
                if code_to_insert:
                    send_command_to_vscode({"action": "show_insert_code_prompt", "code": code_to_insert})
                visual_context = None
            else:
                visual_context = None

            # Generate the response using the model
            response = groq_prompt(prompt=clean_prompt, img_context=visual_context)
            translated_response = translate_text(response, language)
            send_command_to_vscode({"action": "insertOutput", "value": f"ASSISTANT: {translated_response}"})
            
            # Check if the response contains code, and handle accordingly
            code_to_copy = extract_code(response)
            if code_to_copy:
                try:
                    pyperclip.copy(code_to_copy)
                  #  send_command_to_vscode({"action": "insertOutput", "value": "Code copied to clipboard successfully!"})
                    send_command_to_vscode({"action": "show_insert_code_prompt", "code": code_to_copy})
                except pyperclip.PyperclipException as e:
                    send_command_to_vscode({"action": "insertOutput", "value": f"Failed to copy code to clipboard: {e}"})
            else:
                send_command_to_vscode({"action": "insertOutput", "value": "No code block detected in the response."})
            
            filtered_response = filter_code(translated_response)
            audio_manager.speak(filtered_response)
    else:
        print("No valid prompt found.", file=sys.stderr)

def start_listening():
    """Start listening for audio input."""
    with source as s:
        r.adjust_for_ambient_noise(s, duration=1)
        print('Listening...', file=sys.stderr)
        audio = r.listen(s)
        print('Stopped listening.', file=sys.stderr)
        threading.Thread(target=process_audio, args=(audio,)).start()

# Event loop to process commands from the extension
while True:
    command = input().strip()
    if command == "startListening":
        start_listening()
    elif command.startswith("processTextInput:"):
        text = command[len("processTextInput:"):]
        process_text_input(text)
    elif command == "stopSpeaking":
        audio_manager.stop()
