from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, os, configparser, smtplib, base64, io
from email.mime.text import MIMEText
from PIL import Image, ImageOps

def check_image_safe(image_bytes):
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(BASE, 'config.ini'))
    api_key = cfg.get('google', 'vision_api_key', fallback='').strip()
    if not api_key:
        return True  # if not configured, allow through
    try:
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        payload = {
            'requests': [{
                'image': {'content': b64},
                'features': [{'type': 'SAFE_SEARCH_DETECTION'}]
            }]
        }
        resp = requests.post(
            f'https://vision.googleapis.com/v1/images:annotate?key={api_key}',
            json=payload, timeout=10
        )
        result = resp.json()
        print(f'  🔍 Vision API raw response: {result}')
        if 'error' in result:
            print(f'  ⚠  Vision API error: {result["error"]} — allowing through')
            return True
        safe = result['responses'][0].get('safeSearchAnnotation', {})
        print(f'  🔍 SafeSearch: adult={safe.get("adult")} violence={safe.get("violence")} racy={safe.get("racy")}')
        # Block actual nudity. medical=VERY_LIKELY is a known false positive on close-up selfies
        # so we exempt it — but never when adult is VERY_LIKELY (that's real content).
        # Racy alone (tank tops, sexy poses) is not blocked; it only contributes when adult is also elevated.
        is_medical_fp = safe.get('medical') == 'VERY_LIKELY'
        adult = safe.get('adult', 'UNKNOWN')
        racy  = safe.get('racy',  'UNKNOWN')
        adult_blocked    = adult == 'VERY_LIKELY' or (adult == 'LIKELY' and not is_medical_fp)
        racy_combo_block = racy == 'VERY_LIKELY' and adult in ('LIKELY', 'VERY_LIKELY')
        violence_blocked = safe.get('violence') in ('LIKELY', 'VERY_LIKELY')
        if adult_blocked or racy_combo_block or violence_blocked:
            print(f'  🚫 Image BLOCKED by Vision API')
            return False
        print(f'  ✅ Image passed Vision check')
        return True
    except Exception as e:
        print(f'  ⚠  Vision API exception: {e} — allowing through')
        return True

BASE       = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE, 'ImagesForClaude')
app  = Flask(__name__, static_folder=BASE, static_url_path='')
CORS(app)

def get_api_key():
    # Try config.ini first (same file the desktop app uses)
    cfg_path = os.path.join(BASE, 'config.ini')
    if os.path.exists(cfg_path):
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path)
        key = cfg.get('cutout', 'api_key', fallback='').strip()
        if key:
            return key
    # Fall back to environment variable for production server
    return os.environ.get('CUTOUT_API_KEY', '').strip()

@app.route('/')
def index():
    return app.send_static_file('mcfaces.html')

@app.route('/api/skins')
def list_skins():
    folder = os.path.join(BASE, 'Skins')
    if not os.path.isdir(folder):
        return jsonify([])
    results = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != '_thumbs')
        for f in sorted(files):
            if f.lower().endswith('.png'):
                rel = os.path.relpath(os.path.join(root, f), folder)
                results.append(rel.replace('\\', '/'))
    return jsonify(results)

@app.route('/skins/<path:filename>')
def serve_skin(filename):
    return send_from_directory(os.path.join(BASE, 'Skins'), filename)

@app.route('/thumbs/<path:filename>')
def serve_thumb(filename):
    return send_from_directory(os.path.join(BASE, 'Skins', '_thumbs'), filename)

@app.route('/assets/<path:filename>')
def serve_asset(filename):
    return send_from_directory(ASSETS_DIR, filename)

@app.route('/api/alert')
def send_alert():
    try:
        cfg = configparser.ConfigParser()
        cfg.read(os.path.join(BASE, 'config.ini'))
        smtp_server = cfg.get('email', 'smtp_server', fallback='')
        smtp_port   = cfg.getint('email', 'smtp_port',   fallback=587)
        username    = cfg.get('email', 'username',    fallback='')
        password    = cfg.get('email', 'password',    fallback='')
        if not all([smtp_server, username, password]):
            print('  ⚠  Alert: cutout.pro credits empty (email not configured in config.ini)')
            return jsonify({'status': 'email not configured'})
        msg = MIMEText('Your cutout.pro credits are empty.\n\nPlease top up your account at https://www.cutout.pro to restore MCFaces service.')
        msg['Subject'] = '🚨 MCFaces Alert: cutout.pro credits empty'
        msg['From']    = username
        msg['To']      = 'thad@redlavatoys.com'
        with smtplib.SMTP(smtp_server, smtp_port) as s:
            s.starttls()
            s.login(username, password)
            s.send_message(msg)
        print('  OK  Alert email sent to thad@redlavatoys.com')
        return jsonify({'status': 'sent'})
    except Exception as e:
        print(f'  ✗  Alert email failed: {e}')
        return jsonify({'status': 'failed', 'error': str(e)})

@app.route('/api/remove-bg', methods=['POST'])
def remove_bg():
    api_key = get_api_key()
    if not api_key:
        return jsonify({'error': 'API key not configured on server. Add it to config.ini.'}), 500
    matting_type = request.args.get('mattingType', '3')
    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'no file'}), 400
    image_bytes = f.read()
    if not check_image_safe(image_bytes):
        return jsonify({'error': 'inappropriate_content'}), 400
    # Apply EXIF orientation so sideways phone photos are upright for the AI
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=95)
        image_bytes = buf.getvalue()
    except Exception:
        pass
    print(f'  → Sending to cutout.pro: {len(image_bytes)} bytes, mattingType={matting_type}')
    resp = requests.post(
        f'https://www.cutout.pro/api/v1/matting2?mattingType={matting_type}',
        headers={'APIKEY': api_key},
        files={'file': (f.filename, io.BytesIO(image_bytes), 'image/jpeg')},
        timeout=45,
    )
    data = resp.json()
    print(f'  ← cutout.pro response: code={data.get("code")} msg={data.get("msg")} hasBase64={bool(data.get("data",{}).get("imageBase64"))} hasUrl={bool(data.get("data",{}).get("imageUrl"))}')
    return jsonify(data)

if __name__ == '__main__':
    key = get_api_key()
    print(f'\n  MCFaces running at  http://localhost:5000')
    print(f'  API key: {"configured OK" if key else "NOT FOUND — add to config.ini"}\n')
    app.run(debug=False, port=5000)
