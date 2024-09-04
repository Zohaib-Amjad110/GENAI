import * as vscode from "vscode";
import { getNonce } from "./getNonce";

export class SidebarProvider implements vscode.WebviewViewProvider {
  _view?: vscode.WebviewView;

  constructor(
    private readonly _extensionUri: vscode.Uri,
    private readonly context: vscode.ExtensionContext
  ) {}

  public resolveWebviewView(webviewView: vscode.WebviewView) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri],
    };

    webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

    // Restore the conversation when the webview is loaded
    const conversation = this.context.workspaceState.get<string[]>(
      "conversation",
      []
    );
    conversation.forEach((message) => {
      this.insertOutput(message);
    });

    webviewView.webview.onDidReceiveMessage(async (data) => {
      switch (data.type) {
        case "startListening":
          vscode.commands.executeCommand("newExt.startListening");
          break;
        case "submitText":
          vscode.commands.executeCommand("newExt.submitText", data.value);
          break;
        case "stopSpeaking":
          vscode.commands.executeCommand("newExt.stopSpeaking");
          break;
        case "insertOutput":
          this.insertOutput(data.value);
          this.saveConversation(data.value); // Save each new output to workspace state
          break;
        case "clearOutput":
          this.clearOutput();
          break;
      }
    });
  }

  public insertOutput(value: string) {
    if (this._view) {
      this._view.webview.postMessage({
        type: "insertOutput",
        value: value,
      });
    }
  }

  private saveConversation(output: string) {
    const conversation = this.context.workspaceState.get<string[]>(
      "conversation",
      []
    );
    conversation.push(output);
    this.context.workspaceState.update("conversation", conversation);
  }

  private clearOutput() {
    if (this._view) {
      this._view.webview.postMessage({
        type: "clearOutput",
      });
    }
    this.context.workspaceState.update("conversation", []); // Clear the stored conversation
  }

  private _getHtmlForWebview(webview: vscode.Webview): string {
    const styleResetUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this._extensionUri, "media", "reset.css")
    );
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this._extensionUri, "out", "compiled/sidebar.js")
    );
    const styleMainUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this._extensionUri, "out", "compiled/sidebar.css")
    );
    const nonce = getNonce();

    return `<!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta http-equiv="Content-Security-Policy" content="img-src https: data:; style-src 'unsafe-inline' ${
          webview.cspSource
        }; script-src 'nonce-${nonce}';">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="${styleResetUri}" rel="stylesheet">
        <link href="${styleMainUri}" rel="stylesheet">
        <style>
          body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
            padding: 15px;
            margin: 0;
          }

          #output {
            width: 100%;
            height: calc(100vh - 230px);
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            border: 1px solid var(--vscode-editorGroup-border);
            padding: 15px;
            overflow-y: auto;
            white-space: pre-wrap;
            margin-bottom: 15px;
            border-radius: 4px;
            box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.1);
           
          }

          .message-container {
            display: flex;
            margin-bottom: 10px;
          }

          .message {
            padding: 10px;
            border-radius: 10px;
            max-width: 75%;
            word-wrap: break-word;
          }

          .user-message {
            background-color: #0078d4;
            color: white;
            margin-left: auto;
          }

          .assistant-message {
            background-color: #cfcccb;
            color: black;
            margin-right: auto;
          }

          .button-icon {
            background: none;
            border: none;
            cursor: pointer;
            padding: 5px;
            margin-left: 5px;
            vertical-align: middle;
          }

          input[type="text"] {
            width: calc(100% - 90px); /* Adjust width to fit icons */
            padding: 12px;
            margin-bottom: 15px;
            border: 1px solid var(--vscode-input-border);
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: var(--vscode-font-size);
            box-shadow: inset 0px 1px 3px rgba(0, 0, 0, 0.1);
            display: inline-block;
          }

          input[type="text"]::placeholder {
            color: var(--vscode-input-placeholderForeground);
          }

          #input-container {
            display: flex;
            align-items: center;
          }

          #clear-output {
            position: absolute;
            right: 15px;
            top: 15px;
            background: none;
            border: none;
            cursor: pointer;
            padding: 5px;
            font-size: 20px;
          }

        </style>
      </head>
      <body>
        <div id="output"></div>
        <button id="clear-output">×</button> <!-- Clear output button -->
        <div id="input-container">
          <input type="text" id="user-input" placeholder="Type your text here...">
          <button id="submit-text" class="button-icon" title="Submit Text">
            <img src="https://img.icons8.com/material-outlined/24/000000/send.png" alt="Submit">
          </button>
          <button id="start-listening" class="button-icon" title="Voice Input">
            <img src="https://img.icons8.com/material-outlined/24/000000/microphone.png" alt="Voice Input">
          </button>
          <button id="stop-speaking" class="button-icon" title="Stop Speaking">
            <img src="https://img.icons8.com/material-outlined/24/000000/stop.png" alt="Stop Speaking">
          </button>
        </div>
        <script nonce="${nonce}">
          const vscode = acquireVsCodeApi();

          document.getElementById('submit-text').addEventListener('click', () => {
            const userInput = document.getElementById('user-input').value;
            vscode.postMessage({ type: 'submitText', value: userInput });
            document.getElementById('user-input').value = ''; // Clear the input field after submitting
          });

          document.getElementById('start-listening').addEventListener('mousedown', () => {
            vscode.postMessage({ type: 'startListening' });
          });

          document.getElementById('stop-speaking').addEventListener('click', () => {
            vscode.postMessage({ type: 'stopSpeaking' });
          });

          document.getElementById('clear-output').addEventListener('click', () => {
            vscode.postMessage({ type: 'clearOutput' });
            document.getElementById('output').innerHTML = ''; // Clear the output div
          });

          window.addEventListener('message', event => {
            const message = event.data;
            const outputDiv = document.getElementById('output');
            let messageHtml = '';
            if (message.type === 'insertOutput') {
              if (message.value.startsWith('USER:')) {
                messageHtml = \`<div class="message-container"><div class="message user-message">\${message.value.replace('USER:', '').trim()}</div></div>\`;
              } else {
                messageHtml = \`<div class="message-container"><div class="message assistant-message">\${message.value.replace('ASSISTANT:', '').trim()}</div></div>\`;
              }
              outputDiv.innerHTML += messageHtml;
              outputDiv.scrollTop = outputDiv.scrollHeight;
            } else if (message.type === 'clearOutput') {
              document.getElementById('output').innerHTML = '';
            }
          });
        </script>
      </body>
      </html>`;
  }
}
