// content.js - Injects prompts from Second Brain into ChatGPT
// Updated to work with ChatGPT's ProseMirror contenteditable editor
// Auto-submit setelah prompt masuk

(function() {
  "use strict";

  // ambil parameter 'ask' dari URL
  const params = new URLSearchParams(window.location.search);
  const prompt = params.get("ask");

  if (!prompt) return;

  console.log("[Second Brain] Detected prompt, waiting for editor...");

  const decodedPrompt = decodeURIComponent(prompt);

  // tunggu sampe editor siap
  function waitForEditor(maxAttempts) {
    return new Promise(function(resolve, reject) {
      var attempts = 0;

      function check() {
        attempts++;

        // coba beberapa selector buat dapetin editor
        // 1. ProseMirror contenteditable (yang utama)
        var editor = document.querySelector("#prompt-textarea[contenteditable='true']");
        
        // 2. fallback ke class ProseMirror
        if (!editor) {
          editor = document.querySelector("div.ProseMirror[contenteditable='true']");
        }

        // 3. fallback ke contenteditable apapun di form
        if (!editor) {
          editor = document.querySelector("form [contenteditable='true']");
        }

        if (editor) {
          console.log("[Second Brain] Editor found after " + attempts + " attempts");
          resolve(editor);
        } else if (attempts >= maxAttempts) {
          reject(new Error("Editor not found after " + maxAttempts + " attempts"));
        } else {
          setTimeout(check, 500);
        }
      }

      check();
    });
  }

  // auto-submit: klik tombol send
  function autoSubmit() {
    console.log("[Second Brain] Auto-submitting prompt...");

    // tunggu bentar biar UI update dulu
    setTimeout(function() {
      // cari send button
      var sendButton = 
        document.querySelector("#composer-submit-button") ||
        document.querySelector("[data-testid='send-button']") ||
        document.querySelector("button[aria-label='Send prompt']");

      if (sendButton && !sendButton.disabled) {
        sendButton.click();
        console.log("[Second Brain] Prompt submitted!");
      } else if (sendButton && sendButton.disabled) {
        // button disabled, coba tunggu sampe enabled
        console.log("[Second Brain] Send button disabled, waiting...");
        var waitAttempts = 0;
        var waitInterval = setInterval(function() {
          waitAttempts++;
          if (!sendButton.disabled) {
            sendButton.click();
            console.log("[Second Brain] Prompt submitted!");
            clearInterval(waitInterval);
          } else if (waitAttempts >= 20) {
            // fallback: tekan Enter di editor
            console.log("[Second Brain] Button still disabled, trying Enter key...");
            var editor = document.querySelector("#prompt-textarea[contenteditable='true']") ||
                         document.querySelector("div.ProseMirror[contenteditable='true']");
            if (editor) {
              editor.dispatchEvent(new KeyboardEvent("keydown", {
                key: "Enter",
                code: "Enter",
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true,
              }));
            }
            clearInterval(waitInterval);
          }
        }, 300);
      } else {
        // button gak ketemu, fallback: tekan Enter
        console.log("[Second Brain] Send button not found, trying Enter key...");
        var editor = document.querySelector("#prompt-textarea[contenteditable='true']") ||
                     document.querySelector("div.ProseMirror[contenteditable='true']");
        if (editor) {
          editor.dispatchEvent(new KeyboardEvent("keydown", {
            key: "Enter",
            code: "Enter",
            keyCode: 13,
            which: 13,
            bubbles: true,
            cancelable: true,
          }));
        }
      }
    }, 800); // delay 800ms setelah inject
  }

  // inject text ke editor
  function injectIntoEditor(editor) {
    console.log("[Second Brain] Injecting prompt into editor...");

    // fokus editor dulu
    editor.focus();

    // cara 1: pake execCommand (paling reliable buat ProseMirror/React)
    var injected = false;
    try {
      // select all existing content
      var selection = window.getSelection();
      var range = document.createRange();
      range.selectNodeContents(editor);
      selection.removeAllRanges();
      selection.addRange(range);

      // insert text via execCommand
      document.execCommand("insertText", false, decodedPrompt);
      console.log("[Second Brain] Injected via execCommand");
      injected = true;
    } catch (e) {
      console.log("[Second Brain] execCommand failed, trying fallback...");

      // cara 2: set innerHTML langsung + dispatch event
      try {
        // konversi newlines ke paragraph tags buat ProseMirror
        var paragraphs = decodedPrompt.split("\n").map(function(line) {
          return "<p>" + (line || "<br>") + "</p>";
        }).join("");

        editor.innerHTML = paragraphs;

        // dispatch input event
        editor.dispatchEvent(new InputEvent("input", {
          bubbles: true,
          cancelable: true,
          inputType: "insertText",
          data: decodedPrompt,
        }));

        console.log("[Second Brain] Injected via innerHTML + InputEvent");
        injected = true;
      } catch (e2) {
        console.log("[Second Brain] innerHTML failed, trying textContent...");

        // cara 3: textContent + event
        editor.textContent = decodedPrompt;
        editor.dispatchEvent(new Event("input", { bubbles: true }));
        injected = true;
      }
    }

    // juga update hidden textarea (fallback)
    var hiddenTextarea = document.querySelector("textarea[name='prompt-textarea']");
    if (hiddenTextarea) {
      hiddenTextarea.value = decodedPrompt;
      hiddenTextarea.dispatchEvent(new Event("input", { bubbles: true }));
    }

    // bersihin URL parameter
    var cleanUrl = window.location.origin + window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);

    if (injected) {
      console.log("[Second Brain] Prompt injected successfully! Auto-submitting...");
      editor.scrollIntoView({ behavior: "smooth", block: "center" });
      
      // auto-submit setelah inject berhasil
      autoSubmit();
    }
  }

  // jalanin
  waitForEditor(30).then(injectIntoEditor).catch(function(err) {
    console.error("[Second Brain] Failed: " + err.message);
    // retry sekali lagi setelah delay panjang
    setTimeout(function() {
      waitForEditor(20).then(injectIntoEditor).catch(function(err2) {
        console.error("[Second Brain] Final attempt failed: " + err2.message);
      });
    }, 3000);
  });
})();