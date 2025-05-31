from flask import Blueprint, request, jsonify
from supabase_client.supabase_client import get_supabase_client

session_bp = Blueprint("session", __name__)
supabase = get_supabase_client()

@session_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    device_id = data.get("device_id")  # Kullanıcının cihaz ID'si

    if not device_id:
        return jsonify({"error": "Eksik bilgiler"}), 400

    try:
        # Önce bu device_id ile kayıtlı kullanıcı var mı kontrol et
        existing_user = supabase.table('USER').select("*").eq("device_id", device_id).execute()

        if existing_user.data:
            # Kullanıcı zaten varsa bilgilerini döndür
            return jsonify({"message": "Kullanıcı zaten kayıtlı!", "user": existing_user.data[0]}), 201

        # Eğer kayıtlı değilse yeni kullanıcı ekle
        response = supabase.table('USER').insert({
            "device_id": device_id,
        }).execute()

        # Response'u kontrol edelim
        print("Response:", response)  # Debug için
        
        if not response.data:
            return jsonify({"message": "Kullanıcı kaydedildi fakat veri dönmedi"}), 201
            
        return jsonify({"message": "Kullanıcı başarıyla kaydedildi!", "user": response.data[0]}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
