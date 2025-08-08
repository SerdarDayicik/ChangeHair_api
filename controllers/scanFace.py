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
    "male": [
        "Textured Crop",
        "Buzz Cut + Fade", 
        "Modern Pompadour",
        "Bro Flow",
        "Wolf Cut",
        "Side Part Fade",
        "French Crop"
    ],
    "female": [
        # Eski unisex stiller artık kadın kategorisinde
        "Straight",
        "Wavy", 
        "Curly",
        "Layered",
        "Dreadlocks",
        "Cornrows",
        "Perm",
        # Mevcut kadın stilleri
        "Bob",
        "Pixie Cut",
        "Sideswept Pixie",
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
        Bu yüz resmini DETAYLİ olarak analiz et ve aşağıdaki kriterleri kullanarak doğru yüz şeklini belirle:

        YÜZÜN ÖLÇÜMSEL ANALİZİNİ YAP:
        1. Yüzün en geniş noktasını tespit et (alın, yanaklar, çene?)
        2. Yüz uzunluğu ile genişliği arasındaki oranı hesapla
        3. Çene hattının şeklini incele (keskin, yuvarlak, sivri?)
        4. Alın genişliği ile çene genişliğini karşılaştır
        5. Yanakların çıkıntı durumunu değerlendir

        YÜZ ŞEKİLLERİNİN DETAYLI TARİFLERİ:
        - OVAL: Yüz uzunluğu genişlikten 1.5 kat fazla, alın ve çene neredeyse eşit genişlikte, yumuşak hatlar
        - ROUND: Yüz uzunluğu ve genişliği neredeyse eşit, yuvarlak çene hattı, dolgun yanaklar
        - SQUARE: Güçlü çene hattı, alın ve çene genişliği eşit, keskin köşeler, maskülen hatlar
        - HEART: Geniş alın, dar sivri çene, üçgen şeklinde daralma
        - DIAMOND: Dar alın, geniş yanaklar, dar çene, elmasa benzer şekil
        - OBLONG: Oval'e benzer ama daha uzun, yüz uzunluğu genişlikten 2 kat fazla
        - TRIANGLE: Dar alın, geniş çene, ters kalp şekli

        ANALİZ ADIMLARI:
        1. Önce kişinin cinsiyetini belirle (male/female)
        2. Yukarıdaki kriterleri kullanarak yüz ölçümlerini değerlendir
        3. En uygun yüz şeklini seç (sadece bir tane seç)
        4. Seçimini gerekçelendir (hangi özellikler bu yüz şekline işaret ediyor)

        Mevcut saç modelleri kategorilere göre:
        - Male: {', '.join(HAIRCUT_STYLES_DATA['male'])}
        - Female: {', '.join(HAIRCUT_STYLES_DATA['female'])}

        ÖNEMLİ: Her yüz şekli için en uygun saç modellerini seç:
        - Oval: Hemen hemen her stil uygun
        - Round: Yüzü uzatan stiller (katmanlı, uzun)
        - Square: Yumuşatan stiller (dalgalı, katmanlı)
        - Heart: Çeneyi dolgunlaştıran stiller (bob, lob)
        - Diamond: Yanakları dengeleyen stiller
        - Oblong: Yüzü genişleten stiller (yanlardan hacimli)

        Lütfen SADECE bu formatta JSON objesi ile yanıtla:
        {{
            "gender": "male/female",
            "face_shape": "tespit edilen yüz şekli",
            "face_analysis_reason": "Bu yüz şeklini seçme gerekçesi (hangi özellikler buna işaret ediyor)",
            "recommended_hairstyles": ["stil1", "stil2", "stil3", "stil4", "stil5"]
        }}

        DİKKAT: Yüzü gerçekten DİKKATLE incele ve farklı yüz şekillerini ayırt et. Aynı cevabı verme, her yüzün kendine özgü yapısı var!
        Cinsiyete göre sadece o kategorideki saç modellerini öner!
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