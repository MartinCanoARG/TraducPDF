# TraducPDF
#### Video Demo: <https://youtu.be/iHOXoU3GNX8>

#### Description:

TraducPDF is a web application designed to simplify the translation of PDF files quickly, easily, and with the support of artificial intelligence. The main goal of this project is to provide students, teachers, and professionals with a free and accessible tool to translate academic or technical content across different languages while preserving the document’s structure.

The user simply uploads a PDF file, selects the target language, and clicks “Translate.” In a few seconds, the app processes the file, translates the content using the OpenAI GPT API, and returns a new PDF with the translated text, ready for download. The process is seamless and focused on real-world usability.

---

### Technologies Used:

- **Python** – Main backend programming language.
- **Flask** – Lightweight web framework for routing and server logic.
- **HTML5 + CSS3 + JavaScript** – Frontend interface.
- **OpenAI API** – Used to translate text with contextual accuracy.
- **pdfplumber** – To extract text content from PDF files.
- **ReportLab** – To generate new PDF files with the translated content.
- **SQLite** (optional for future versions with user accounts/history).

---

### Project Structure:

- `app.py` – Contains the core logic of the backend, including file upload, text extraction, translation request, and PDF generation.
- `templates/index.html` – Frontend interface allowing users to upload files and choose target language.
- `static/` – Contains custom CSS styles and assets.
- `.env` – Hidden file with sensitive API keys (excluded from repository).
- `README.md` – This documentation file.

---

### Design Decisions:

Several libraries were evaluated for PDF processing. `pdfplumber` was chosen for accurate text extraction, and `ReportLab` was used for generating clean, structured translated PDFs. The OpenAI API offered better contextual translations than traditional tools, especially with technical documents.

Flask was selected for its simplicity and scalability. The architecture is modular and can be easily extended to include user authentication, translation history, or cloud storage integration in future releases.

---

### Future Improvements:

- Implement OCR support for scanned PDFs or text inside images.
- Better handling of complex layouts and multi-column documents.
- Preserve styles such as bold, headings, and text formatting.
- Add user login system with file history and download tracking.

---

This project was created by **Martín Cano** as the final submission for **CS50's Introduction to Computer Science (CS50x 2025)**.  
GitHub: [MartinCanoARG](https://github.com/MartinCanoARG)  
City: Rosario, Argentina  
Recording Date: May 7th, 2025
