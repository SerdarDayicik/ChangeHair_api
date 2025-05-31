from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from supabase_client.supabase_client import get_supabase_client
import replicate
import os
import requests
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename  # Dosya adı güvenliği için
import json  # JSON string'i parse etmek için

# .env dosyasını yüklüyoruz
load_dotenv()

model_bp = Blueprint("model", __name__)
supabase = get_supabase_client()

# Uploads klasörünü oluştur
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)

@model_bp.route('/change-hair', methods=['POST'])
def change_hair():
    try:
        # Form-data'dan dosyayı ve diğer bilgileri al
        if 'image' not in request.files:
            return jsonify({"error": "Resim dosyası gerekli"}), 400
            
        if 'data' not in request.form:
            return jsonify({"error": "data alanı gerekli"}), 400

        # Form'dan verileri al
        image = request.files['image']
        data = json.loads(request.form['data'])  # JSON string'i parse et
        
        # Data'dan gerekli bilgileri çıkar
        device_id = data.get('device_id')
        gender = data.get('gender', 'none')
        haircut = data.get('haircut', 'Random')
        hair_color = data.get('hair_color', 'Random')
        aspect_ratio = data.get('aspect_ratio', 'match_input_image')

        if not device_id:
            return jsonify({"error": "device_id gerekli"}), 400

        if image.filename == '':
            return jsonify({"error": "Resim seçilmedi"}), 400

        # Gelen resmi kaydet
        input_filename = f"{uuid.uuid4()}.png"  # Uzantıyı .png olarak sabitledik
        input_file_path = UPLOAD_FOLDER / input_filename
        image.save(input_file_path)

        # View-image endpoint'i üzerinden resim URL'i oluştur
        input_image_url = f"{request.host_url.rstrip('/')}/model/view-image/{input_filename}?device_id={device_id}"

        # Replicate modelini çalıştır
        output = replicate.run(
            "flux-kontext-apps/change-haircut",
            input={
                "gender": gender,
                "haircut": haircut,
                "hair_color": hair_color,
                "input_image": input_image_url,
                "aspect_ratio": aspect_ratio
            }
        )
        
        # FileOutput'u string'e çevir
        output_url = str(output) if output else None

        if not output_url:
            return jsonify({"error": "Model çıktısı alınamadı"}), 500

        # Oluşturulan görseli indir
        response = requests.get(output_url)
        if response.status_code != 200:
            return jsonify({"error": "Görsel indirilemedi"}), 500

        # Oluşturulan görsel için rastgele dosya adı oluştur
        output_filename = f"{uuid.uuid4()}.png"
        output_file_path = UPLOAD_FOLDER / output_filename

        # Oluşturulan görseli kaydet
        with open(output_file_path, 'wb') as f:
            f.write(response.content)

        # Oluşturulan görselin URL'ini oluştur
        output_image_url = f"/uploads/{output_filename}"

        # Supabase'e kaydet
        try:
            supabase.table('user_images').insert({
                "device_id": device_id,
                "user_image": input_image_url,  # Kullanıcının yüklediği resmin URL'i
                "generated_image": output_image_url,  # Oluşturulan resmin URL'i
                "gender": gender,
                "haircut_style": haircut,
                "haircut_color": hair_color
            }).execute()
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")

        return jsonify({
            "success": True,
            "message": "Görsel başarıyla oluşturuldu ve kaydedildi",
            "input_image_url": input_image_url,
            "output_image_url": output_image_url,
            "original_output_url": output_url
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@model_bp.route('/view-image/<image_name>', methods=['GET'])
def viewImage(image_name):
    try:
        # Query parametresinden device_id al
        device_id = request.args.get('device_id')

        if not device_id:
            return jsonify({
                "error": "device_id parametresi gerekli"
            }), 400

        # Önce kullanıcının varlığını kontrol et
        user_response = supabase.table('USER').select("*").eq("device_id", device_id).execute()

        if not user_response.data:
            return jsonify({
                "error": "Yetkisiz erişim. Kullanıcı bulunamadı."
            }), 403

        # Resim dosyasının yolunu oluştur
        image_path = UPLOAD_FOLDER / image_name

        # Resim dosyasının varlığını kontrol et
        if not image_path.exists():
            return jsonify({
                "error": "Resim bulunamadı"
            }), 404

        # Resmi gönder
        from flask import send_file
        return send_file(
            image_path,
            mimetype='image/png'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@model_bp.route('/user-images/<device_id>', methods=['GET'])
def getUserImages(device_id):
    try:
        # Kullanıcının tüm resimlerini getir
        response = supabase.table('user_images').select("*").eq("device_id", device_id).execute()

        if not response.data:
            return jsonify({
                "message": "Bu kullanıcıya ait resim bulunamadı",
                "images": []
            }), 200

        return jsonify({
            "success": True,
            "images": response.data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
