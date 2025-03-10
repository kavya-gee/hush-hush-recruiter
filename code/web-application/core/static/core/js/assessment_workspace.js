import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { sql } from "@codemirror/lang-sql";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { oneDark } from "@codemirror/theme-one-dark";

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the editor
    let editor;
    let currentLanguage = document.getElementById("language-select").value;
    const codeSubmissionField = document.getElementById("code-submission");
    const codeLanguageField = document.getElementById("code-language");

    // Setup language support
    function getLanguageExtension(language) {
        switch(language) {
            case "python":
                return python();
            case "javascript":
                return javascript();
            case "sql":
                return sql();
            case "html":
                return html();
            case "css":
                return css();
            default:
                return python();
        }
    }

    // Create the editor
    function createEditor(language) {
        const editorContainer = document.getElementById("code-editor");

        // Get initial code or use empty string
        const initialCode = codeSubmissionField.value || "";

        const editorState = EditorState.create({
            doc: initialCode,
            extensions: [
                basicSetup,
                getLanguageExtension(language),
                oneDark,
                EditorView.updateListener.of(update => {
                    if (update.docChanged) {
                        // Update the hidden form field with current code
                        codeSubmissionField.value = update.state.doc.toString();
                    }
                })
            ]
        });

        return new EditorView({
            state: editorState,
            parent: editorContainer
        });
    }

    // Initialize the editor
    editor = createEditor(currentLanguage);

    // Change language
    function changeLanguage() {
        const languageSelect = document.getElementById("language-select");
        const language = languageSelect.value;
        currentLanguage = language;

        // Update the hidden language field
        codeLanguageField.value = language;

        // Dispose of the old editor
        if (editor) {
            // Keep the current code
            const currentCode = editor.state.doc.toString();
            editor.destroy();

            // Create a new editor with the selected language but keep the current code
            codeSubmissionField.value = currentCode;
            editor = createEditor(language);
        }
    }

    // Assign the function to the global scope for access from HTML
    window.changeLanguage = changeLanguage;

    // Run code
    function runCode() {
        if (!editor) return;

        const code = editor.state.doc.toString();
        const language = document.getElementById("language-select").value;
        const outputContainer = document.getElementById("output-container");

        // Simulate code execution
        outputContainer.innerHTML += `<div class="output-run">Running ${language} code...</div>`;

        setTimeout(() => {
            // This is a simulation - in a real implementation this would execute the code
            if (language === "python") {
                outputContainer.innerHTML += `<div class="output-result">
                    <pre>Python simulation output</pre>
                </div>`;
            } else if (language === "javascript") {
                outputContainer.innerHTML += `<div class="output-result">
                    <pre>JavaScript simulation output</pre>
                </div>`;
            } else if (language === "sql") {
                outputContainer.innerHTML += `<div class="output-result">
                    <pre>SQL query results would appear here</pre>
                    <table>
                        <tr><th>id</th><th>name</th><th>value</th></tr>
                        <tr><td>1</td><td>Sample</td><td>Result</td></tr>
                    </table>
                </div>`;
            }
            outputContainer.scrollTop = outputContainer.scrollHeight;
        }, 1000);
    }

    // Reset code to starter code
    function resetCode() {
        if (confirm("Are you sure you want to reset your code to the original starter code? This cannot be undone.")) {
            // Reset by reloading the page
            window.location.reload();
        }
    }

    // Clear output
    function clearOutput() {
        document.getElementById("output-container").innerHTML = "";
    }

    // Toggle question panel
    function toggleQuestionPanel() {
        const questionPanel = document.querySelector(".question-panel");
        const editorPanel = document.querySelector(".editor-panel");

        if (questionPanel.classList.contains("collapsed")) {
            questionPanel.classList.remove("collapsed");
            questionPanel.style.width = "40%";
            editorPanel.style.width = "60%";
        } else {
            questionPanel.classList.add("collapsed");
            questionPanel.style.width = "0";
            editorPanel.style.width = "100%";
        }
    }

    // Assign event handlers
    document.getElementById("run-code").addEventListener("click", runCode);
    document.getElementById("reset-code").addEventListener("click", resetCode);
    document.getElementById("clear-output").addEventListener("click", clearOutput);
    window.toggleQuestionPanel = toggleQuestionPanel;

    // Handle keyboard shortcuts
    document.addEventListener("keydown", function(e) {
        // Ctrl+Enter to run code
        if (e.ctrlKey && e.key === "Enter") {
            e.preventDefault();
            runCode();
        }
    });

    // Timer functionality - using the original logic
    let totalSeconds = parseInt(document.getElementById("total-seconds").value);

    function updateTimer() {
        if (totalSeconds <= 0) {
            document.getElementById('hours').textContent = "0";
            document.getElementById('minutes').textContent = "0";
            document.getElementById('seconds').textContent = "0";
            alert("Time's up! Your assessment will be automatically submitted.");
            document.getElementById('code-form').submit();
            return;
        }

        totalSeconds--;
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        document.getElementById('hours').textContent = hours;
        document.getElementById('minutes').textContent = minutes;
        document.getElementById('seconds').textContent = seconds;
    }

    // Update timer every second
    setInterval(updateTimer, 1000);

    // Update the submit button to use form submission
    document.querySelector(".btn-submit").addEventListener("click", function(e) {
        e.preventDefault();

        // Update the form fields one last time
        codeSubmissionField.value = editor.state.doc.toString();
        codeLanguageField.value = document.getElementById("language-select").value;

        // Submit the form
        document.getElementById('code-form').submit();
    });
});