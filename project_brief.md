# Project Brief: LegalKG — Legal Knowledge Graph & Regulatory Intelligence Platform

## 📋 Executive Summary
**LegalKG** adalah platform *knowledge graph* hukum berbasis *open-source* yang dirancang khusus untuk mengotomatisasi pengumpulan, pemodelan, dan analisis hubungan kompleks antar peraturan perundang-undangan di Indonesia. 

Platform ini secara mandiri meng-curate (*crawl/scrape*) data hukum dari portal resmi **JDIH BPK (https://peraturan.bpk.go.id)**, membangun jaringan keterkaitan regulasi (misal: undang-undang yang mencabut, mengubah, atau menjadi dasar delegasi peraturan di bawahnya), dan menyediakan antarmuka **Graph-Augmented RAG** berbasis LLM (OpenAI / Google Gemini). Pengguna (Advokat, Legal Officer, Akademisi) dapat melakukan pencarian semantik dan mengajukan pertanyaan hukum kompleks dalam bahasa natural dengan jawaban yang akurat, kontekstual, serta minim halusinasi.

---

## ⚙️ Core Workflow

* **Data Ingestion (`ingestion/`)**  
  Bot *crawler* modular mengunduh metadata, dokumen PDF peraturan, dan status hukum (diubah, mencabut, dll.) langsung dari URL target `peraturan.bpk.go.id`.
* **Entity & Relation Extraction (`extraction/`)**  
  LLM menganalisis teks undang-undang/peraturan (PDF) untuk mengekstrak entitas hukum, pasal-pasal kunci, rujukan antar-regulasi, lalu memetakan relasinya dengan *confidence score*.
* **Graph Storage (`graph/`)**  
  Neo4j Community Edition menyimpan data ke dalam skema graf hukum (skema *hierarkis* dan *kronologis*) dengan indeks vektor terintegrasi.
* **Graph-Augmented RAG Interface (`llm/`)**  
  User mengajukan pertanyaan dalam bahasa natural $\rightarrow$ Sistem melakukan pencarian *hybrid* (Vektor + Subgraph) $\rightarrow$ Diterjemahkan ke penjelasan semantik hukum yang komprehensif lengkap dengan dasar hukum (pasal/ayat).

---

## 🏗️ System Architecture

### Backend Stack
* **Framework:** FastAPI (Python 3.10+)
* **Scraping & Parsing:** Scrapy / BeautifulSoup4, Selenium/Playwright (untuk dynamic rendering), dan PyMuPDF/PDFPlumber untuk ekstraksi teks PDF Peraturan.
* **Graph Database:** Neo4j Community Edition
* **LLM & Embedding:** 
  * OpenAI API (`gpt-4o`, `text-embedding-3-small`) **ATAU**
  * Google Gemini API (`gemini-1.5-pro` — *direkomendasikan untuk context window dokumen hukum yang panjang*, `text-embedding-004`)
* **Vector Index:** Neo4j Vector Index (Built-in, tidak perlu service terpisah)
* **Streaming:** Server-Sent Events (SSE) untuk progress scraping & ekstraksi real-time.

### Frontend Stack
* **Framework:** Next.js (TypeScript)
* **Graph Explorer:** Cytoscape.js / D3-force (visualisasi interaktif silsilah hukum)
* **UI Components:** TailwindCSS, Shadcn UI
* **Data Binding:** Fetch API, Zustand (state management)

---

## 🎯 Target Data Source (https://peraturan.bpk.go.id)

Sistem akan fokus melakukan *scraping* secara berkala pada komponen berikut:
* **Metadata Peraturan:** Judul, Nomor, Tahun, Jenis Peraturan (UU, PP, PERPRES, PERMEN, Perda), Tanggal Disahkan, Tanggal Diundangkan.
* **Status Hukum:** Tabel keterkaitan regulasi seperti *"Mengubah"*, *"Diubah Oleh"*, *"Mencabut"*, *"Dicabut Oleh"*, *"Menjadi Dasar Delegasi Dari"*.
* **Dokumen Fisik:** Unduh berkas PDF resmi untuk di-ekstrak konten teksnya per bab, pasal, hingga ayat.

---

## 🗂️ Definisi Graph Schema (Legal Domain)

### Entitas (Nodes)
* `Peraturan`: Produk hukum secara utuh (contoh: *UU No. 11 Tahun 2008*).
* `Pasal`: Unit terkecil dari peraturan (contoh: *Pasal 27*).
* `Ayat`: Sub-unit dari pasal (contoh: *Ayat 3*).
* `Lembaga`: Instansi yang mengeluarkan/menandatangani (contoh: *Presiden, Menkominfo*).
* `KonsepHukum`: Istilah, subjek, atau topik hukum (contoh: *Pencemaran Nama Baik, Transaksi Elektronik*).

### Relasi (Edges)
* `MENCABUT` / `DICABUT_OLEH` (Peraturan $\rightarrow$ Peraturan)
* `MENGUBAH` / `DIUBAH_OLEH` (Peraturan $\rightarrow$ Peraturan)
* `DASAR_DELEGASI` (Peraturan $\rightarrow$ Peraturan) — *Tata urutan perundangan (e.g., UU mendelegasikan ke PP).*
* `BAGIAN_DARI` (Pasal $\rightarrow$ Peraturan / Ayat $\rightarrow$ Pasal)
* `MERUJUK_KE` (Pasal $\rightarrow$ Pasal) — *Apabila ada pasal yang menyebutkan "Sebagaimana dimaksud pada pasal X..."*
* `MENGATUR` (Pasal $\rightarrow$ KonsepHukum)

---

## 📂 Directory Structure

```text
legalkg/
├── ingestion/
│   ├── scrapers/
│   │   ├── bpk_crawler.py           # Scraper utama untuk peraturan.bpk.go.id
│   │   └── pdf_processor.py         # Ekstraktor teks PDF peraturan & pemisah Bab/Pasal
│   └── pipeline.py                  # Orkestrator jadwal scraping berkala (Celery/APScheduler)
│
├── extraction/
│   ├── legal_extractor.py           # LLM NER untuk mendeteksi istilah hukum & rujukan pasal
│   └── prompts/
│       └── legal_extraction_prompt.txt # Prompt khusus ekstraksi UU/Peraturan Indonesia
│
├── graph/
│   ├── neo4j_client.py              # Koneksi & helper Cypher query
│   └── schemas/
│       └── legal_schema.cypher      # Definisi constraints dan indeks Neo4j
│
├── llm/
│   ├── rag_engine.py                # Graph-Augmented RAG Engine (Hybrid Search)
│   ├── nl2cypher.py                 # Translator pertanyaan user ke Cypher query
│   └── vector_search.py             # Manajemen embedding teks pasal hukum
│
├── api/
│   ├── app.py                       # FastAPI Endpoint Entrypoint
│   └── routes/
│       ├── chat.py                  # Endpoint untuk RAG Chatbot hukum
│       ├── ingest.py                # Trigger & monitoring scraper
│       └── graph.py                 # Endpoint visualisasi silsilah regulasi
│
├── frontend/
│   ├── app/                         # Next.js App Router
│   │   ├── page.tsx                 # Chatbot Dashboard Interface
│   │   └── explorer/page.tsx        # Visualizer silsilah hukum
│   └── components/
│       └── GraphCanvas.tsx          # Cytoscape.js wrapper
│
├── docker-compose.yml               # Neo4j + Backend + Frontend
├── requirements.txt
└── README.md