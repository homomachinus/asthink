"""
Second Brain - Knowledge Graph Builder
Cara pakai:
  1. pip install streamlit requests pymupdf pdfplumber pyvis networkx
  2. Isi key.json sama API keys lo
  3. Jalanin: streamlit run main.py
"""

from src.app import main


if __name__ == "__main__":
    main()
