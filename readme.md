# Second Brain

Aplikasi knowledge graph builder yang pake OCR dan AI buat ngebangun "otak kedua" lo. Upload dokumen, extract text, AI extract entities, terus masukin ke knowledge graph yang bisa lo explore dan tanyain lebih lanjut ke ChatGPT.

---

## Daftar Isi

- [Apa Ini](#apa-ini)
- [Pipeline](#pipeline)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Setup](#setup)
- [Konfigurasi API Keys](#konfigurasi-api-keys)
- [Cara Pakai](#cara-pakai)
  - [Tab Ingest](#tab-ingest)
  - [Tab Knowledge Graph](#tab-knowledge-graph)
  - [Ask ChatGPT](#ask-chatgpt)
- [Chrome Extension](#chrome-extension)
- [Knowledge Graph JSON Structure](#knowledge-graph-json-structure)
- [Entity Extraction](#entity-extraction)
- [Export](#export)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Tech Stack](#tech-stack)

---

## Apa Ini

Second Brain itu aplikasi buat ngebangun knowledge graph dari dokumen-dokumen lo. Flow-nya gini:

1. Lo upload dokumen (PDF, gambar, URL, atau paste text)
2. Mistral OCR extract semua text dari dokumen itu
3. 9Router (lokal AI router) extract entities - topik utama, subtopik, konsep, relasi, dll
4. Semua entities masuk ke knowledge graph yang persistent
5. Lo bisa explore graph-nya secara visual
6. Kalo mau belajar lebih dalem soal satu topik, klik aja dan langsung ke ChatGPT dengan context lengkap

Intinya: dokumen masuk, knowledge graph keluar. Semakin banyak dokumen yang lo masukin, semakin kaya graph-nya. Dan karena entity extraction-nya aware sama topics yang udah ada, dokumen baru otomatis ke-link ke topik yang udah ada kalau emang related.

---

## Pipeline

```
                    Input
        PDF / Image / URL / Paste Text
                        |
                        v
              Ingestion Layer (Step 1-2)
              Mistral OCR (Pixtral Model)
              Extract raw text from documents
                        |
                        v
              AI Processing (Step 3)
              9Router Entity Extraction
              Topics, Subtopics, Entities,
              Relationships, Tags
                        |
                        v
              Knowledge Graph (Step 4)
              Persistent JSON Storage
              Auto-merge with existing topics
              Interactive Visualization
                        |
                        v
              ChatGPT Integration
              Click any node -> open ChatGPT
              with full context prompt
              Auto-inject + auto-submit
                        
           [ Future Steps ]
                        
              Vector Database (Step 5)
              Embedding + Semantic Search
                        
              Retrieval (Step 6)
              RAG-based Q&A over your knowledge
```

Yang udah jalan: Step 1-4 + ChatGPT integration.
Yang belum: Step 5-6 (vector store dan retrieval).

---

## Project Structure

```
second-brain/
|
|-- main.py                     # Main app (Streamlit, ~800 lines)
|-- key.json                    # API keys (Mistral + 9Router)
|-- knowledge_graph.json        # Persistent graph database
|-- requirements.txt            # Python dependencies
|-- .gitignore                  # Git ignore (key.json included)
|-- .streamlit/
|   |-- config.toml             # Streamlit theme config
|
|-- chrome-extension/           # Chrome extension for ChatGPT
|   |-- manifest.json           # Extension manifest (V3)
|   |-- content.js              # Prompt injector script
|   |-- README.md               # Extension docs
|
|-- output/                     # Auto-saved exports
|   |-- brain_YYYYMMDD_HHMMSS.json
|
|-- uploads/                    # File staging (auto-created)
```

---

## Requirements

- Python 3.10+ (tested on 3.10 and 3.11)
- pip
- Google Chrome (buat extension)
- 9Router running di localhost (default: port 20128)
- Mistral AI API key

---

## Setup

### 1. Clone / Copy Project

```bash
cd D:\second-brain
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Dependencies yang di-install:
- `streamlit` - UI framework
- `requests` - HTTP client buat API calls
- `pymupdf` - PDF text extraction dan rendering
- `pdfplumber` - Fallback PDF text extraction
- `pyvis` - Interactive graph visualization
- `networkx` - Graph data structure

### 3. Setup API Keys

Bikin file `key.json` di root folder:

```json
{
  "mistral": {
    "api_key": "your-mistral-api-key"
  },
  "9router": {
    "api_key": "",
    "base_url": "http://localhost:20128/v1",
    "model": ""
  }
}
```

Detail ada di bagian [Konfigurasi API Keys](#konfigurasi-api-keys).

### 4. Install Chrome Extension

Lihat bagian [Chrome Extension](#chrome-extension).

### 5. Run the App

```bash
streamlit run main.py
```

Browser otomatis buka di `http://localhost:8501`.

---

## Konfigurasi API Keys

### Mistral AI (OCR)

1. Daftar di https://console.mistral.ai
2. Ke API Keys section
3. Generate new key
4. Copy ke `key.json` di bagian `mistral.api_key`

Model yang dipake: `pixtral-12b-2409` (vision model, optimized buat OCR).

### 9Router (Entity Extraction)

9Router itu lokal AI router yang jalan di machine lo. Setup-nya tergantung gimana lo install 9Router-nya.

Default config:
- Base URL: `http://localhost:20128/v1`
- API Key: kosong (karena lokal, biasanya gak perlu)
- Model: kosong (auto-route) atau specify model name

Lo bisa ubah model di sidebar app langsung tanpa edit `key.json`.

### Kenapa pake JSON file buat keys?

Biar gampang di-manage. Satu file buat semua keys. Dan karena masuk `.gitignore`, gak bakal ke-commit ke git. Aman.

---

## Cara Pakai

### Tab Ingest

Tab ini buat masukin dokumen baru ke knowledge graph.

#### Upload Files

Drag and drop atau klik buat pilih file. Support:
- **Images**: JPG, JPEG, PNG, BMP, TIFF, WEBP, GIF
- **Documents**: PDF

Bisa upload multiple files sekaligus.

#### Image URL

Paste URL gambar yang mau di-OCR. Harus direct link ke gambar (bukan link ke halaman web).

#### Paste Text

Kalo lo punya text yang udah di-copy dari mana aja, paste aja langsung. Gak perlu OCR, langsung masuk ke entity extraction.

#### Processing Flow

1. Klik "Extract and Build Graph"
2. OCR jalan dulu (buat PDF/image)
3. Hasil OCR dikirim ke 9Router buat entity extraction
4. Entities di-merge ke knowledge graph
5. Kalo ada topik yang sama dengan yang udah ada, otomatis ke-link

Progress bar nunjukin proses per file.

#### Results

Setelah proses selesai, lo liat:
- **Metrics**: jumlah file, entities yang di-extract, total nodes dan edges di graph
- **Per-document breakdown**:
  - Main Topics (biru) - topik utama
  - Subtopics (hijau) - subtopik dengan parent
  - Entities (orange) - konsep, orang, organisasi, teknologi
  - Relationships - relasi antar entities
  - Tags - keywords
- **Raw extracted text** - text mentah dari OCR

### Tab Knowledge Graph

Tab ini buat explore knowledge graph yang udah ke-build.

#### Interactive Graph Visualization

Di bagian atas ada graph interaktif (pake pyvis/vis.js):
- **Nodes**: colored by type (biru = main topic, hijau = subtopic, orange = entity, abu-abu = tag)
- **Edges**: labeled dengan relationship type
- **Drag**: klik dan geser nodes
- **Zoom**: scroll buat zoom in/out
- **Hover**: hover node buat liat detail + [Ask ChatGPT] link

#### Node List

Di bawah graph ada list semua nodes, bisa di-filter:
- **Filter by type**: All, Main Topic, Subtopic, Entity, Tag
- **Search**: ketik buat filter berdasarkan nama

Setiap node yang di-expand nunjukin:
- Type
- Description
- Parent topic (kalo ada)
- Source documents
- Connections (nodes yang ke-link)

#### Ask ChatGPT

Setiap node punya tombol "Ask ChatGPT about this topic". Klik ini bakal:

1. **Build prompt** yang include:
   - Nama topik dan type-nya
   - Full description
   - Parent topic
   - Semua connected nodes dan descriptions-nya
   - Source documents
   - Study questions
2. **URL encode** prompt-nya
3. **Buka ChatGPT** di tab baru dengan `?ask=encoded_prompt`
4. **Chrome extension** auto-inject prompt ke textarea
5. **Auto-submit** - prompt langsung dikirim

Jadi lo literally tinggal klik dan ChatGPT langsung jawab dengan konteks lengkap dari knowledge graph lo.

Selain tombol di node list, ada juga `[Ask ChatGPT]` link di hover tooltip setiap node di graph visualization.

#### Danger Zone

Tombol "Reset Knowledge Graph" buat hapus semua nodes dan edges. Pake double-confirm biar gak kepencet.

---

## Chrome Extension

Extension ini yang bikin integration sama ChatGPT jalan. Dia detect parameter `?ask=` di URL ChatGPT dan auto-inject prompt-nya.

### Install

1. Buka Chrome
2. Ketik `chrome://extensions/` di address bar
3. Aktifkan **Developer mode** (toggle di kanan atas)
4. Klik **Load unpacked**
5. Pilih folder `second-brain/chrome-extension`
6. Extension muncul di list, pastikan enabled

### Cara Kerja

```
1. User klik [Ask ChatGPT] di Second Brain
2. Browser buka: https://chatgpt.com/?ask=encoded_prompt
3. Extension detect parameter "ask" di URL
4. Tunggu ChatGPT editor siap (ProseMirror contenteditable)
5. Inject prompt ke editor (pake execCommand)
6. Tunggu 800ms
7. Klik tombol send (#composer-submit-button)
8. ChatGPT langsung proses
9. URL parameter dihapus (biar gak re-trigger kalo refresh)
```

### Technical Details

- **Manifest V3** - standar Chrome extension terbaru
- **Content script** - cuma jalan di `https://chatgpt.com/*`
- **3 injection methods** dengan fallback:
  1. `document.execCommand("insertText")` - paling reliable buat ProseMirror
  2. `innerHTML` + `InputEvent` - fallback pertama
  3. `textContent` + `Event` - fallback terakhir
- **Auto-submit** - klik send button atau fallback ke Enter key
- **Retry logic** - tunggu sampe 30 attempts (15 detik) buat editor muncul

### Update Extension

Kalo ada update ke `content.js`:
1. Buka `chrome://extensions/`
2. Klik tombol refresh di extension card
3. Refresh tab ChatGPT

---

## Knowledge Graph JSON Structure

File `knowledge_graph.json` itu database graph lo. Structure-nya:

```json
{
  "nodes": {
    "machine_learning": {
      "id": "machine_learning",
      "label": "Machine Learning",
      "type": "main_topic",
      "description": "Study of algorithms that improve through experience",
      "parent_topic": "",
      "sources": ["textbook.pdf", "lecture_notes.jpg"],
      "created_at": "2026-06-14T12:00:00",
      "updated_at": "2026-06-14T14:30:00"
    },
    "neural_networks": {
      "id": "neural_networks",
      "label": "Neural Networks",
      "type": "subtopic",
      "description": "Computing systems inspired by biological neural networks",
      "parent_topic": "Machine Learning",
      "sources": ["textbook.pdf"],
      "created_at": "2026-06-14T12:00:00",
      "updated_at": "2026-06-14T12:00:00"
    }
  },
  "edges": [
    {
      "key": "machine_learning->neural_networks:subtopic_of",
      "source": "machine_learning",
      "target": "neural_networks",
      "relation": "subtopic_of",
      "context": "Neural Networks is a subtopic of Machine Learning"
    }
  ],
  "sources": [
    "textbook.pdf",
    "lecture_notes.jpg"
  ]
}
```

### Node Types

| Type | Warna | Deskripsi |
|------|-------|-----------|
| `main_topic` | Biru (#667eea) | Topik utama, high-level subject |
| `subtopic` | Hijau (#38ef7d) | Sub-bagian dari main topic |
| `entity` | Orange (#fcb69f) | Konsep spesifik, orang, organisasi, teknologi |
| `tag` | Abu-abu (#e0e0e0) | Keywords buat categorization |

### Edge Relations

Relasi yang bisa ada antar nodes:
- `subtopic_of` - A adalah subtopik dari B
- `contains` - A mengandung entity B
- `uses` - A menggunakan B
- `requires` - A membutuhkan B
- `related_to` - A berhubungan dengan B
- `enables` - A memungkinkan B
- `competes_with` - A bersaing dengan B
- `part_of` - A adalah bagian dari B
- `influences` - A mempengaruhi B

### Node ID

Node ID itu slug dari nama (lowercase, spasi jadi underscore, max 80 chars). Ini dipake buat deduplikasi - kalo ada entity baru yang namanya sama dengan yang udah ada, dia merge ke node yang existing.

### Source Tracking

Setiap node track dari dokumen mana aja dia di-extract. Jadi lo bisa tau "oh topik ini gue dapet dari dokumen A dan B".

---

## Entity Extraction

### How It Works

Entity extraction pake 9Router (AI model di belakangnya). Prompt-nya minta AI buat:

1. **Main Topics** - identifikasi subjek utama
2. **Subtopics** - area spesifik di bawah main topic
3. **Entities** - konsep, orang, organisasi, teknologi, terms
4. **Relationships** - gimana entities relate satu sama lain
5. **Tags** - keywords singkat

### Smart Merging

Pas extract entities dari dokumen baru, AI juga dikasih list topik yang udah ada di graph. Jadi kalo ada topik yang sama atau related, AI pake nama yang exact sama biar bisa ke-link.

Contoh:
- Dokumen 1 extract "Machine Learning" sebagai main topic
- Dokumen 2 juga bahas ML -> AI recognize "Machine Learning" udah ada -> merge ke node yang sama
- Node "Machine Learning" sekarang punya 2 sources

### Truncation

Kalo text yang di-OCR terlalu panjang (> 12,000 characters), dia di-truncate dulu sebelum dikirim ke 9Router. Ini biar gak exceed token limit.

### JSON Parsing

Response dari 9Router harusnya valid JSON. Tapi kadang AI wrap JSON-nya di markdown code block. Script-nya handle ini:
1. Coba parse langsung
2. Kalo gagal, cari JSON object di dalam response
3. Kalo masih gagal, report error

---

## Export

### Auto-Save

Setiap kali extract entities, hasilnya otomatis di-save ke `knowledge_graph.json`. Gak perlu manual save.

### Manual Export

Di tab Ingest, setelah proses selesai, ada 2 tombol export:

1. **Download Graph JSON** - download `knowledge_graph.json` saat itu
2. **Download Full Export** - download semua data termasuk:
   - Timestamp
   - Semua extraction results
   - Full graph state

File export masuk ke folder `output/` juga secara otomatis.

### Export Formats (dari Ingest tab)

- `.json` - full structured data
- `.txt` - plain text (raw text + summary per document)
- `.md` - markdown formatted

---

## Troubleshooting

### "Mistral OCR: No key"

- Cek `key.json` ada di root folder (`D:\second-brain\key.json`)
- Cek format JSON valid
- Cek `mistral.api_key` gak kosong

### "Cannot connect to 9Router"

- Cek 9Router jalan di `http://localhost:20128`
- Cek port yang bener
- Update `key.json` -> `9router.base_url` kalo port-nya beda

### "9Router returned non-JSON response"

- Biasanya karena 9Router return streaming response
- Pastikan `"stream": false` di payload (udah di-handle di code)
- Cek model name di sidebar / `key.json`

### "Cannot read PDF. Install pymupdf."

```bash
pip install pymupdf
```

### Graph visualization gak muncul

```bash
pip install pyvis networkx
```

### Chrome extension gak inject prompt

1. Cek extension enabled di `chrome://extensions/`
2. Refresh extension
3. Refresh tab ChatGPT
4. Cek console (F12) buat error messages dari `[Second Brain]`

### Prompt masuk tapi gak auto-submit

- Kadang ChatGPT butuh waktu buat enable send button
- Extension udah ada retry logic (tunggu sampe 6 detik)
- Kalo masih gagal, tekan Enter manual

### Streamlit config error (TOML parse)

- File `.streamlit/config.toml` harus UTF-8 tanpa BOM
- Kalo error, hapus file dan bikin ulang

### BOM issues (garbled text, parse errors)

PowerShell `Set-Content -Encoding UTF8` nambahin BOM. Fix:
```powershell
$content = Get-Content file.txt -Raw
[System.IO.File]::WriteAllText("file.txt", $content, [System.Text.UTF8Encoding]::new($false))
```

---

## Roadmap

### Current (Done)

- [x] Upload documents (PDF, images, URLs, paste text)
- [x] Mistral OCR text extraction
- [x] PDF text layer extraction + OCR fallback
- [x] 9Router entity extraction
- [x] Knowledge graph building with auto-merge
- [x] Interactive graph visualization
- [x] Node filtering and search
- [x] ChatGPT integration (prompt building + auto-inject + auto-submit)
- [x] Chrome extension for ChatGPT
- [x] Export to JSON, TXT, MD
- [x] Persistent graph storage

### Next Steps

- [ ] **Vector Store** - Embed semua extracted text pake embedding model, simpan di vector database (ChromaDB / Pinecone / Qdrant)
- [ ] **Semantic Retrieval** - Search knowledge graph pake natural language, RAG-based Q&A
- [ ] **Video Support** - Speech-to-text dari video, extract knowledge dari video content
- [ ] **Auto-tagging** - Automatic tagging dan categorization
- [ ] **Graph Analytics** - centrality analysis, topic clustering, knowledge gap detection
- [ ] **Multi-user** - Shared knowledge graphs
- [ ] **Mobile** - Responsive bottom navigation

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI Framework | Streamlit |
| OCR | Mistral AI (Pixtral 12B) |
| AI Router | 9Router (local, OpenAI-compatible API) |
| Entity Extraction | LLM via 9Router |
| Graph Visualization | pyvis (vis.js) |
| Graph Data | JSON file storage |
| PDF Processing | PyMuPDF + pdfplumber |
| ChatGPT Integration | Chrome Extension (Manifest V3) |
| Language | Python 3.10+ |
| HTTP Client | requests |

---

## License

Personal project. Use it however you want.
