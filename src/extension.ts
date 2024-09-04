import * as vscode from 'vscode';
import { SidebarProvider } from './SidebarProvider';
import * as cp from 'child_process';
import * as path from 'path';

let pythonProcess: cp.ChildProcess | null = null;

export function activate(context: vscode.ExtensionContext) {
    console.log('Congratulations, your extension "newExt" is now active!');

    // Register the sidebar
    const sidebarProvider = new SidebarProvider(context.extensionUri, context); // Pass context
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            "zohaib-sidebar",
            sidebarProvider,
            { webviewOptions: { retainContextWhenHidden: true } }
        )
    );

    // Register the Start Listening command
    context.subscriptions.push(
        vscode.commands.registerCommand('newExt.startListening', () => {
            startListening();
        })
    );

    // Register the Submit Text command
    context.subscriptions.push(
        vscode.commands.registerCommand('newExt.submitText', (text: string) => {
            processTextInput(text);
        })
    );

    // Register the Stop Speaking command
    context.subscriptions.push(
        vscode.commands.registerCommand('newExt.stopSpeaking', () => {
            stopSpeaking();
        })
    );

    // Register the Show Sidebar command (triggered by Ctrl+E)
    context.subscriptions.push(
        vscode.commands.registerCommand('newExt.showSidebar', async () => {
            // Open the sidebar
            await vscode.commands.executeCommand('workbench.view.extension.zohaib-sidebar-view');
        })
    );

    // Register the insertOutput command
    context.subscriptions.push(
        vscode.commands.registerCommand('zohaib-sidebar.insertOutput', (output: string) => {
            sidebarProvider.insertOutput(output);
        })
    );

    // Start the Python backend when the extension is activated
    startPythonBackend(context);
}

export function deactivate() {
    if (pythonProcess) {
        pythonProcess.kill();
    }
}

// Function to start the Python backend
function startPythonBackend(context: vscode.ExtensionContext) {
    if (!pythonProcess) {
        const pythonPath = 'python'; // Ensure this points to your Python executable
        const scriptPath = path.join(context.extensionPath, 'back.py'); // Path to your back.py file

        pythonProcess = cp.spawn(pythonPath, [scriptPath]);

        let dataBuffer = '';

        pythonProcess.stdout?.on('data', data => {
            dataBuffer += data.toString();

            // Split the buffer by newlines to handle multiple JSON objects
            const messages = dataBuffer.split('\n');
            dataBuffer = messages.pop() || '';  // Keep any incomplete JSON object

            for (const message of messages) {
                if (message.trim()) {
                    try {
                        const jsonObject = JSON.parse(message);
                        handlePythonMessage(jsonObject);
                    } catch (error) {
                        console.error('Failed to parse message from Python process:', error);
                    }
                }
            }
        });

        pythonProcess.stderr?.on('data', data => {
            console.error(`Python stderr: ${data}`);
        });

        pythonProcess.on('close', code => {
            console.log(`Python process exited with code ${code}`);
            if (code !== 0) {
                vscode.window.showErrorMessage(`Python process exited with code ${code}`);
            }
            pythonProcess = null;
        });

        vscode.window.showInformationMessage('Python backend started');
    }
}

// This function handles the messages received from the Python process
function handlePythonMessage(message: any) {
    if (message.action === 'insertOutput') {
        vscode.commands.executeCommand('zohaib-sidebar.insertOutput', message.value);
    } else if (message.action === 'show_insert_code_prompt') {
        showInsertCodePrompt(message.code);
    }
}

// Function to show a popup asking if the user wants to insert code
function showInsertCodePrompt(code: string) {
    vscode.window.showInformationMessage('Code detected. Do you want to insert it into the editor?', 'Yes', 'No').then(selection => {
        if (selection === 'Yes') {
            clearEditor();
            typeCodeInEditor(code);
        }
    });
}

// Function to clear the active editor's content
function clearEditor() {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
        const document = editor.document;
        const edit = new vscode.WorkspaceEdit();
        const fullRange = new vscode.Range(
            document.positionAt(0),
            document.positionAt(document.getText().length)
        );
        edit.delete(document.uri, fullRange);
        vscode.workspace.applyEdit(edit);
    }
}

// Function to type code into the editor line by line
async function typeCodeInEditor(code: string) {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
        // Split the code by lines
        const lines = code.split('\n');
        for (const line of lines) {
            await editor.edit(editBuilder => {
                editBuilder.insert(editor.selection.active, line + '\n');
            });
            await sleep(150); // Delay to simulate typing speed
        }
    }
}

// Function to start listening
function startListening() {
    if (pythonProcess && pythonProcess.stdin) {
        pythonProcess.stdin.write('startListening\n');
        vscode.window.showInformationMessage('Started listening...');
    } else {
        vscode.window.showErrorMessage('Python process is not running');
    }
}

// Function to process text input
function processTextInput(text: string) {
    if (pythonProcess && pythonProcess.stdin) {
        pythonProcess.stdin.write(`processTextInput:${text}\n`);
    } else {
        vscode.window.showErrorMessage('Python process is not running');
    }
}

// Function to stop speaking
function stopSpeaking() {
    if (pythonProcess && pythonProcess.stdin) {
        pythonProcess.stdin.write('stopSpeaking\n');
        vscode.window.showInformationMessage('Stopped Speaking ...');
    } else {
        vscode.window.showErrorMessage('Python process is not running');
    }
}

// Helper function to simulate typing delay
function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
