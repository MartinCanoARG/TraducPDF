import os
import io
import sqlite3
import tempfile
import pdfplumber
import requests
import openai
import fitz

from flask import Flask, session, redirect, render_template, request, url_for, jsonify, send_file, flash
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

# Cargar variables de entorno
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Conexión con base de datos

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                hash TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS pdfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                text TEXT NOT NULL,
                translated BOOLEAN,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        db.commit()

init_db()

# Funciones auxiliares

def traducir_texto(texto, idioma_destino, idioma_origen="auto"):
    if idioma_origen == "auto":
        prompt = f"Traduce el siguiente texto al idioma {idioma_destino.upper()}:"
    else:
        prompt = f"Traduce el siguiente texto del idioma {idioma_origen.upper()} al idioma {idioma_destino.upper()}:"

    try:
        respuesta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": texto}
            ],
            max_tokens=3000
        )
        return respuesta.choices[0].message["content"].strip()
    except Exception as e:
        try:
            url = "https://api-free.deepl.com/v2/translate"
            params = {
                "auth_key": DEEPL_API_KEY,
                "text": texto,
                "target_lang": idioma_destino.upper()
            }
            response = requests.post(url, data=params)
            data = response.json()
            return data["translations"][0]["text"]
        except:
            return "[ERROR] No se pudo traducir el texto."

def generar_respuesta_simulada(carrera):
    respuestas = {
        "medicina": "Simulación IA: El contenido será procesado para medicina.",
        "derecho": "Simulación IA: El contenido será procesado para derecho.",
        "ingenieria": "Simulación IA: El contenido será procesado para ingeniería.",
        "otra": "Simulación IA: Procesamiento general."
    }
    return respuestas.get(carrera, respuestas["otra"])

def extraer_imagenes_del_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    imagenes = []
    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            bbox = page.get_image_bbox(xref)
            imagenes.append({
                "page": page_number,
                "bbox": bbox,
                "image_bytes": image_bytes
            })
    doc.close()
    return imagenes

def crear_pdf_traducido_con_imagenes(texto_traducido, imagenes_extraidas):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_file.name, pagesize=letter)
    width, height = letter
    margin = 40
    y_position = height - margin

    imagenes_por_pagina = {}
    for img in imagenes_extraidas:
        imagenes_por_pagina.setdefault(img["page"], []).append(img)

    lineas = texto_traducido.split('\n')
    pagina_actual = 0

    for linea in lineas:
        if pagina_actual in imagenes_por_pagina:
            for img in imagenes_por_pagina[pagina_actual]:
                image_reader = ImageReader(io.BytesIO(img["image_bytes"]))
                x0, y0, x1, y1 = img["bbox"]
                ancho = x1 - x0
                alto = y1 - y0
                c.drawImage(image_reader, x0, height - y1, width=ancho, height=alto)

        if y_position < margin:
            c.showPage()
            pagina_actual += 1
            y_position = height - margin

        c.drawString(margin, y_position, linea[:100])
        y_position -= 15

    c.save()
    return temp_file.name

# Rutas principales

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/upload")
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("upload.html")

@app.route("/process-pdf", methods=["POST"])
def process_pdf():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo PDF"}), 400

    file = request.files['file']
    translate = request.form.get('translate') == 'true'
    language = request.form.get('language')
    source_lang = request.form.get('source_lang', 'auto')
    career = request.form.get('career')

    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    if not career:
        return jsonify({"error": "No se seleccionó ninguna carrera"}), 400

    try:
        with pdfplumber.open(file) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'

        if translate and language:
            text = traducir_texto(text, language, source_lang)

        respuesta_ia = generar_respuesta_simulada(career)

        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        file.save(temp_pdf.name)
        imagenes_extraidas = extraer_imagenes_del_pdf(temp_pdf.name)

        nuevo_pdf_path = crear_pdf_traducido_con_imagenes(text, imagenes_extraidas)

        db = get_db()
        db.execute(
            "INSERT INTO pdfs (user_id, filename, text, translated, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
            (session["user_id"], file.filename, text, translate)
        )
        db.commit()

        return jsonify({
            "texto_procesado": text,
            "respuesta_ia": respuesta_ia,
            "download_link": f"/download-translated?path={nuevo_pdf_path}"
        })

    except Exception as e:
        print("⚠️ Error en /process-pdf:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    pdfs = db.execute(
        "SELECT id, filename, translated, timestamp FROM pdfs WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()

    return render_template("history.html", pdfs=pdfs)

@app.route("/pdfs/<int:pdf_id>")
def view_pdf(pdf_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    pdf = db.execute(
        "SELECT id, filename, text, translated, timestamp FROM pdfs WHERE id = ? AND user_id = ?",
        (pdf_id, session["user_id"])
    ).fetchone()

    if not pdf:
        return "PDF no encontrado", 404

    return render_template("view_pdf.html", pdf=pdf)

@app.route("/download/<int:pdf_id>")
def download_pdf(pdf_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    pdf = db.execute(
        "SELECT filename, text FROM pdfs WHERE id = ? AND user_id = ?",
        (pdf_id, session["user_id"])
    ).fetchone()

    if not pdf:
        return "PDF no encontrado", 404

    texto_bytes = io.BytesIO()
    texto_bytes.write(pdf["text"].encode("utf-8"))
    texto_bytes.seek(0)

    nombre_archivo = pdf["filename"].rsplit(".", 1)[0] + ".txt"

    return send_file(
        texto_bytes,
        mimetype="text/plain",
        as_attachment=True,
        download_name=nombre_archivo
    )

@app.route("/delete/<int:pdf_id>", methods=["POST"])
def delete_pdf(pdf_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    pdf = db.execute(
        "SELECT id FROM pdfs WHERE id = ? AND user_id = ?",
        (pdf_id, session["user_id"])
    ).fetchone()

    if not pdf:
        return "No se encontró el PDF o no tienes permiso para borrarlo", 404

    db.execute("DELETE FROM pdfs WHERE id = ?", (pdf_id,))
    db.commit()

    return redirect(url_for("history"))

@app.route("/download-translated")
def download_translated():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "Archivo no encontrado", 404
    return send_file(path, as_attachment=True)

# Usuarios

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Faltan datos", 400

        hash_pw = generate_password_hash(password)
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hash_pw))
            db.commit()
        except sqlite3.IntegrityError:
            return "Usuario ya existe", 400

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user["hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
        else:
            return "Usuario o contraseña incorrectos", 400

    return render_template("login.html")

@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    count_pdfs = db.execute("SELECT COUNT(*) as total FROM pdfs WHERE user_id = ?", (session["user_id"],)).fetchone()
    return render_template("profile.html", username=user["username"], total_pdfs=count_pdfs["total"])

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

        if not check_password_hash(user["hash"], old_password):
            return "Contraseña anterior incorrecta", 400

        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", (new_hash, session["user_id"]))
        db.commit()
        return redirect(url_for("profile"))

    return render_template("change_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)