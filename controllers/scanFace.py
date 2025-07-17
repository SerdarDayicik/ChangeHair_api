from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
import os
import json
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# .env dosyasını yüklüyoruz
load_dotenv()

scan_bp = Blueprint("scan", __name__)

# Gemini Client'ını yapılandır
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Saç modelleri verileri
HAIRCUT_STYLES_DATA = {
    "unisex": [
        "No change",
        "Straight",
        "Wavy", 
        "Curly",
        "Layered",
        "Dreadlocks",
        "Cornrows",
        "Perm"
    ],
    "male": [
        "Undercut",
        "Mohawk",
        "Tousled",
        "Crew Cut",
        "Faux Hawk",
        "Slicked Back",
        "Side-Parted",
        "Center-Parted",
        "Razor Cut",
        "Mohawk Fade",
        "Zig-Zag Part"
    ],
    "female": [
        "Bob",
        "Pixie Cut",
        "Messy Bun",
        "High Ponytail",
        "Low Ponytail",
        "Braided Ponytail",
        "French Braid",
        "Double Dutch Braids",
        "Top Knot",
        "Blunt Bangs",
        "Side-Swept Bangs",
        "Shag",
        "Lob",
        "Angled Bob",
        "Soft Waves",
        "Feathered",
        "Pageboy",
        "Pigtails",
        "Twist Out",
        "Box Braids",
        "Crown Braid",
        "Rope Braid",
        "Chignon",
        "Messy Chignon",
        "Updo",
        "Ballerina Bun",
        "Beehive",
        "Half-Up, Half-Down",
        "Messy Bun with a Scarf"
    ]
}

def analyze_face_with_gemini(image_file):
    """Gemini API ile yüz analizi yapar - doğrudan file objesi alır"""
    try:
        # Flask FileStorage objesini PIL Image'e çevir
        image_bytes = image_file.read()
        image = Image.open(BytesIO(image_bytes))
        
        # Prompt'u hazırla
        text_input = f"""
        Bu yüz resmini analiz et ve aşağıdaki bilgileri JSON formatında ver:

        1. Kişinin cinsiyetini belirle (male/female/unisex)
        2. Yüz şeklini tanımla (oval, round, square, heart, diamond, oblong, vb.)
        3. Yüz şekli ve cinsiyete göre, verilen listeden uygun saç modellerini öner

        Mevcut saç modelleri kategorilere göre:
        - Unisex: {', '.join(HAIRCUT_STYLES_DATA['unisex'])}
        - Male: {', '.join(HAIRCUT_STYLES_DATA['male'])}
        - Female: {', '.join(HAIRCUT_STYLES_DATA['female'])}

        Lütfen SADECE bu formatta JSON objesi ile yanıtla:
        {{
            "gender": "male/female/unisex",
            "face_shape": "tespit edilen yüz şekli",
            "recommended_hairstyles": ["stil1", "stil2", "stil3", "stil4", "stil5"]
        }}

        Yüz şekli ve cinsiyete göre en uygun 5 saç modelini seç. Uygun olduğunda hem unisex hem de cinsiyete özel seçenekleri dahil et.
        """
        
        # Gemini'ye gönder
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[text_input, image],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT']
            )
        )
        
        # Yanıtı al
        response_text = response.candidates[0].content.parts[0].text.strip()
        
        # JSON'u ayıkla (bazen extra metin olabilir)
        if response_text.startswith('```json'):
            response_text = response_text[7:-3]
        elif response_text.startswith('```'):
            response_text = response_text[3:-3]
        
        # JSON'u parse et
        result = json.loads(response_text)
        
        return result
        
    except Exception as e:
        print(f"Gemini API hatası: {str(e)}")
        return None

@scan_bp.route('/analyze-face', methods=['POST'])
def analyze_face():
    try:
        # Form-data'dan dosyayı ve device_id'yi al
        if 'image' not in request.files:
            return jsonify({"error": "Resim dosyası gerekli"}), 400
            
        device_id = request.form.get('device_id')
        if not device_id:
            return jsonify({"error": "device_id gerekli"}), 400

        image = request.files['image']
        
        if image.filename == '':
            return jsonify({"error": "Resim seçilmedi"}), 400

        # Gemini ile yüz analizi yap - doğrudan file objesi gönder
        analysis_result = analyze_face_with_gemini(image)
        
        if not analysis_result:
            return jsonify({"error": "Yüz analizi yapılamadı"}), 500

        return jsonify({
            "success": True,
            "message": "Yüz analizi başarıyla tamamlandı",
            "data": {
                "gender": analysis_result.get('gender'),
                "face_shape": analysis_result.get('face_shape'),
                "recommended_hairstyles": analysis_result.get('recommended_hairstyles')
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500