from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Base directory fix (important for hosting)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

# Create folders if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB


def allowed_file(filename):
    """Allow APK, ZIP, BIN files"""
    allowed = {'apk', 'zip', 'bin'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def derive_key(pkg):
    """Derive encryption key from package name"""
    key = []
    for i in range(32):
        ch = ord(pkg[i % len(pkg)])
        val = ch ^ 0x5A
        val = val ^ (i * 7)
        key.append(val & 0xFF)
    return key


def encrypt(data, key):
    """XOR encryption"""
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

        # Get original extension
        original_ext = request.form.get('original_ext', '').lower()
        
        # Save uploaded file with original name first
        original_filename = secure_filename(file.filename)
        uid = str(uuid.uuid4())[:8]
        temp_path = os.path.join(UPLOAD_FOLDER, f"{uid}_temp_{original_filename}")
        file.save(temp_path)
        
        # If it was ZIP file, rename to APK
        if original_ext == 'zip':
            apk_filename = original_filename.replace('.zip', '.apk') if original_filename.endswith('.zip') else original_filename + '.apk'
            input_path = os.path.join(UPLOAD_FOLDER, f"{uid}_{apk_filename}")
            # Rename the file from .zip to .apk
            os.rename(temp_path, input_path)
            print(f"✅ Renamed ZIP to APK: {original_filename} -> {apk_filename}")
        else:
            input_path = temp_path
            print(f"✅ Processing file as is: {original_filename}")
        
        # Read file
        with open(input_path, 'rb') as f:
            data = f.read()
        
        print(f"📦 File size: {len(data)} bytes")
        
        # Encrypt
        key = derive_key(package_name)
        encrypted = encrypt(data, key)
        
        # Save output - Pehle wala filename
        output_filename = "ṩỹṧ꙱ṫḗṃ.tmp"
        output_path = os.path.join(OUTPUT_FOLDER, f"{uid}_{output_filename}")
        
        with open(output_path, 'wb') as f:
            f.write(encrypted)
        
        # Cleanup input file
        os.remove(input_path)
        
        print(f"✅ Encryption complete. Output: {output_filename}")
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
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
                print(f"🧹 Cleaned up: {filename}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Cleanup error: {str(e)}")
        return jsonify({'success': False})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)