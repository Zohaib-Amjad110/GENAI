# Coding Assistant AI Extension

## Overview

The Coding Assistant AI Extension is a powerful tool integrated with various AI models designed to assist developers with real-time coding tasks. It can explain code, provide debugging tips, offer alternative code suggestions, and more. The extension supports both text and voice commands, making it a versatile assistant for developers.

## Features

- **Real-time Code Assistance**: 
  - Explain specific code blocks, functions, or classes.
  - Identify potential issues and suggest debugging solutions.
  - Provide optimized or alternative code versions.

- **Multilingual Support**: 
  - Auto-detects input language.
  - Translates both user inputs and AI responses into the preferred language.

- **Voice Interaction**: 
  - Use voice commands to interact with the AI.
  - Transcribes speech to text for processing.

- **Code Insertion**: 
  - Automatically insert or simulate typing out code in the active editor.
  - Supports word-by-word typing simulation.

- **Screenshot & Clipboard Integration**: 
  - Capture and analyze screenshots.
  - Extract and process clipboard content for code explanations.

- **Conversation Retention**: 
  - Maintains conversation history across sessions, even when switching tabs.

## Installation

### Prerequisites

- **Python 3.x**
- **Node.js**
- **VS Code**

### Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Zohaib-Amjad110/GENAI.git
2. **Navigate to the Extension Directory:**
   ```bash
   cd GENAI
3. **Install Dependencies**
   ```bash
   npm install
4. **Package Extension**
   ```bash
   vsce package
5. **Package Extension**
    - Open VS Code.
    - Go to the Extensions view (Ctrl+Shift+X).
    - Click the three dots (...) in the top-right corner and select Install from VSIX....
    - Choose the generated .vsix file from step 4.
# Usage
## Starting the Extension
**Open the Sidebar:**
  - Press Ctrl+E to launch the extension's sidebar panel.
## Voice Commands
**Activate Voice Input:**
  - Press and hold the microphone icon to start recording.
  - Release the button to stop and process the voice command.
## Text Commands
**Submit Text:**
 - Type your command in the text input field.
 - Press the send icon to submit the text command.
## Clearing the Output
**Clear Conversation:**
 - Click the clear icon (×) in the top-right corner of the output window to remove the 
   conversation history.
## Code Insertion
**Inserting Code:**
 - When the AI response includes code, the extension will prompt you to insert it into the editor.
 - If confirmed, the code will be automatically typed out in the active editor.
## Configuration
 **API Key Setup**
    - Ensure your API keys for OpenAI, Groq, and Google Generative AI are correctly configured 
      in the back.py file.
# Troubleshooting
## Common Issues
**Voice Commands Not Working:**
 - Check your microphone settings and permissions.
 - Ensure the microphone is correctly configured in your system.
**Translation Issues:**
 - Verify that langdetect and deep-translator are installed and properly configured.
 - Check the source and target languages in your configuration.
**Code Insertion Not Working:**
 - Ensure the active editor is in focus.
 - Verify that the extension is allowed to interact with the editor.
## Contributing
**We welcome contributions! To contribute:**
 - Fork the repository.
 - Create a new branch for your feature or bug fix.
 - Submit a pull request with a detailed explanation of your changes.
**License**
This project is licensed under the MIT License. See the LICENSE file for details.

**Contact**
For any questions or feedback, feel free to reach out zohaibamjad84@gmail.com
    
   
