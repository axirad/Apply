from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, os, configparser, smtplib, base64, io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
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

def _decode_data_url(data_url):
    if ',' in data_url:
        data_url = data_url.split(',', 1)[1]
    return base64.b64decode(data_url)

@app.route('/api/send-print-files', methods=['POST'])
def send_print_files():
    gmail_user = os.environ.get('GMAIL_USER', '').strip()
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD', '').strip()
    if not gmail_user or not gmail_pass:
        print('  ⚠  send-print-files: GMAIL_USER / GMAIL_APP_PASSWORD not set')
        return jsonify({'status': 'email not configured'}), 500
    data = request.get_json(silent=True) or {}
    order_id  = data.get('orderId',  'unknown')
    skin_name = data.get('skinName', 'unknown')
    timestamp = data.get('timestamp', '')
    ua        = data.get('userAgent', '')
    skin_b64  = data.get('skin')
    heads     = data.get('heads') or {}
    if not skin_b64 or not heads:
        return jsonify({'status': 'missing files'}), 400
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f'🎉 ApplyMyFace Order Pending — {order_id} — {skin_name}'
        msg['From']    = gmail_user
        msg['To']      = 'sales@redlavatoys.com'
        body = (
            f'A buyer just clicked Buy Now on applymyface.com.\n\n'
            f'Order ID: {order_id}\n'
            f'Skin:     {skin_name}\n'
            f'Time:     {timestamp}\n'
            f'Browser:  {ua}\n\n'
            f'Note: this fires when Buy is clicked, before checkout. '
            f'Match against actual Shopify orders by approximate timestamp.\n\n'
            f'Attached: skin.png (64×64) + 5 head views (300×300, front/back/left/right/top).'
        )
        msg.attach(MIMEText(body, 'plain'))
        skin_attach = MIMEImage(_decode_data_url(skin_b64), _subtype='png')
        skin_attach.add_header('Content-Disposition', 'attachment', filename=f'{order_id}_skin.png')
        msg.attach(skin_attach)
        for view in ('front', 'back', 'left', 'right', 'top'):
            b64 = heads.get(view)
            if not b64:
                continue
            img = MIMEImage(_decode_data_url(b64), _subtype='png')
            img.add_header('Content-Disposition', 'attachment', filename=f'{order_id}_head_{view}.png')
            msg.attach(img)
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(gmail_user, gmail_pass)
            s.send_message(msg)
        print(f'  OK  Print files emailed to sales@redlavatoys.com — {order_id} — {skin_name}')
        return jsonify({'status': 'sent', 'orderId': order_id})
    except Exception as e:
        print(f'  ✗  send-print-files failed: {e}')
        return jsonify({'status': 'failed', 'error': str(e)}), 500

if __name__ == '__main__':
    key = get_api_key()
    print(f'\n  MCFaces running at  http://localhost:5000')
    print(f'  API key: {"configured OK" if key else "NOT FOUND — add to config.ini"}\n')
    app.run(debug=False, port=5000)
