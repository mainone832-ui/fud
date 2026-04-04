from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'apk', 'zip', 'bin'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    """Encrypt data using XOR with key"""
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
        # Get package name
        package_name = request.form.get('package_name', '').strip()
        if not package_name:
            return jsonify({'error': 'Package name cannot be empty!'}), 400
        
        # Get file
        if 'apk_file' not in request.files:
            return jsonify({'error': 'No file uploaded!'}), 400
        
        file = request.files['apk_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected!'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type! Only APK, ZIP, BIN files allowed!'}), 400
        
        # Save uploaded file
        original_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())[:8]
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{unique_id}_{original_filename}")
        file.save(input_path)
        
        # Read file
        with open(input_path, 'rb') as f:
            plain_data = f.read()
        
        # Derive key and encrypt
        key = derive_key(package_name)
        encrypted_data = encrypt(plain_data, key)
        
        # Save encrypted file
        output_filename = "ṩỹṧ꙱ṫḗṃ.tmp"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{unique_id}_{output_filename}")
        
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Clean up input file
        os.remove(input_path)
        
        # Return file for download
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
    """Clean up output files"""
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        if filename:
            filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

if __name__ == '__main__':
    print("🔐 APK Encryptor Web Server")
    print("=" * 40)
    print("Server running...")
    print("Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=5000)