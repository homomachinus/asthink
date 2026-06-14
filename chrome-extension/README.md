# Second Brain - ChatGPT Prompt Injector

Chrome extension yang inject prompt dari Knowledge Graph ke ChatGPT.

## Cara Install

1. Buka Chrome, ketik `chrome://extensions/` di address bar
2. Aktifkan **Developer mode** (toggle di pojok kanan atas)
3. Klik **Load unpacked**
4. Pilih folder `chrome-extension` ini
5. Done! Extension udah aktif

## Cara Pakai

1. Buka Second Brain app (`streamlit run main.py`)
2. Pergi ke tab **Knowledge Graph**
3. Klik node mana aja yang mau dipelajarin
4. Klik **"Ask ChatGPT about this topic"**
5. ChatGPT bakal kebuka otomatis sama prompt yang lengkap

## Gimana Cara Kerjanya

Extension ini baca parameter `?ask=` dari URL ChatGPT, terus inject text-nya ke textarea. Jadi waktu kamu klik link dari Second Brain, prompt-nya langsung masuk ke ChatGPT tanpa perlu copy-paste.

## Struktur File

- `manifest.json` - Config extension (Manifest V3)
- `content.js` - Script yang jalan di chatgpt.com, inject prompt dari URL parameter

## Notes

- Extension ini cuma jalan di `https://chatgpt.com/*`
- Kalo ChatGPT update UI-nya, mungkin perlu update selector di `content.js`
- Prompt otomatis di-decode dari URL dan masuk ke textarea