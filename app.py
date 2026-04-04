from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Base directory fix (important for hosting)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

ALLOWED_EXTENSIONS = {'apk', 'zip', 'bin'}

# Create folders if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def derive_key(pkg):
    key = []
    for i in range(32):
        ch = ord(pkg[i % len(pkg)])
        val = ch ^ 0x5A
        val = val ^ (i * 7)
        key.append(val & 0xFF)
    return key


def encrypt(data, key):
    output = bytearray(len(data))
    for i in range(len(data)):
        output[i] = data[i] ^ key[i % len(key)]
    return output


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/encrypt', methods=['POST'])
def encrypt_file():
    try:
        package_name = request.form.get('package_name', '').strip()
        if not package_name:
            return jsonify({'error': 'Package name required'}), 400

        if 'apk_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['apk_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Save file
        filename = secure_filename(file.filename)
        uid = str(uuid.uuid4())[:8]
        input_path = os.path.join(UPLOAD_FOLDER, f"{uid}_{filename}")
        file.save(input_path)

        # Read file
        with open(input_path, 'rb') as f:
            data = f.read()

        # Encrypt
        key = derive_key(package_name)
        encrypted = encrypt(data, key)

        # Save output (simple filename - IMPORTANT)
        output_filename = "system.tmp"
        output_path = os.path.join(OUTPUT_FOLDER, f"{uid}_{output_filename}")

        with open(output_path, 'wb') as f:
            f.write(encrypted)

        os.remove(input_path)

        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cleanup', methods=['POST'])
def cleanup():
    try:
        data = request.get_json()
        filename = data.get('filename', '')

        if filename:
            path = os.path.join(OUTPUT_FOLDER, filename)
            if os.path.exists(path):
                os.remove(path)

        return jsonify({'success': True})
    except:
        return jsonify({'success': False})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # IMPORTANT for hosting
    app.run(host='0.0.0.0', port=port)