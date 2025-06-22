from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from supabase_client.supabase_client import get_supabase_client
from datetime import datetime, timedelta




# .env dosyasını yüklüyoruz
load_dotenv()

premiumAndToken_bp = Blueprint("premiumAndToken", __name__)
supabase = get_supabase_client()


@premiumAndToken_bp.route("/premium", methods=["POST"])
def premium():
    try:
        # Request verilerini al
        data = request.get_json()
        device_id = data.get('device_id')
        subscription_expiration = data.get('subscription_expiration')
        subscription_type = data.get('subscription_type')
        last_token_renewal_time = data.get('last_token_renewal_time')

        if not all([device_id, subscription_expiration, subscription_type, last_token_renewal_time]):
            return jsonify({
                "error": "Eksik parametreler",
                "status": False
            }), 400

        # 1. Device ID kontrolü
        user_response = supabase.table('USER').select('*').eq('device_id', device_id).execute()
        
        if not user_response.data:
            return jsonify({
                "error": "Yetkisiz erişim. Device ID bulunamadı.",
                "status": False
            }), 401

        user_data = user_response.data[0]

        # Premium kontrolü
        if user_data.get('is_premium'):
            return jsonify({
                "error": "Bu kullanıcı zaten premium üye",
                "status": False,
                "subscription_info": {
                    "subscription_type": user_data.get('subscription_type'),
                    "subscription_expiration": user_data.get('subscription_expiration'),
                    "credits": user_data.get('credits')
                }
            }), 400

        current_credits = user_data.get('credits', 0)

        # Eğer mevcut credits 0'dan büyükse, önce sıfırla
        if current_credits > 0:
            reset_response = supabase.table('USER').update({
                'credits': 0
            }).eq('device_id', device_id).execute()

        # Subscription type'a göre credit belirleme
        credit_mapping = {
            'yearly': 250,
            'monthly': 150,
            'weekly': 50
        }
        
        credits = credit_mapping.get(subscription_type.lower())
        if credits is None:
            return jsonify({
                "error": "Geçersiz abonelik türü",
                "status": False
            }), 400

        # Update user data
        update_data = {
            'subscription_expiration': subscription_expiration,
            'subscription_type': subscription_type,
            'is_premium': True,
            'credits': credits,
            'last_token_renewal_time': last_token_renewal_time
        }

        update_response = supabase.table('USER').update(update_data).eq('device_id', device_id).execute()

        return jsonify({
            "message": "Premium bilgileri başarıyla güncellendi",
            "status": True,
            "data": update_response.data,
            "previous_credits": current_credits
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": False
        }), 500
    

@premiumAndToken_bp.route("/renewPremium", methods=["POST"])
def renew_premium():
    try:
        # Request verilerini al
        data = request.get_json()
        device_id = data.get('device_id')
        subscription_expiration = data.get('subscription_expiration')
        latest_purchase_date = data.get('latestPurchaseDate')

        # 1. Gerekli alanların kontrolü
        if not all([device_id, subscription_expiration, latest_purchase_date]):
            return jsonify({
                "error": "Eksik parametreler (device_id, subscription_expiration, latestPurchaseDate gerekli)",
                "status": False
            }), 400

        # Device ID kontrolü
        user_response = supabase.table('USER').select('*').eq('device_id', device_id).execute()
        
        if not user_response.data:
            return jsonify({
                "error": "Kullanıcı bulunamadı",
                "status": False
            }), 404

        user_data = user_response.data[0]

        # Premium kullanıcı kontrolü
        if not user_data.get('is_premium'):
            return jsonify({
                "error": "Bu kullanıcı premium üye değil",
                "status": False
            }), 403

        # 2. Tarihleri karşılaştır
        db_last_renewal = datetime.fromisoformat(user_data['last_token_renewal_time'].replace('Z', '+00:00'))
        new_purchase_date = datetime.fromisoformat(latest_purchase_date.replace('Z', '+00:00'))

        # Eğer yeni satın alma tarihi, veritabanındaki son yenileme tarihinden farklı değilse
        if db_last_renewal == new_purchase_date:
            return jsonify({
                "error": "Kredi zaten yüklenmiş",
                "status": False,
                "last_renewal": db_last_renewal.isoformat()
            }), 400

        # 3. Subscription type'a göre credit belirleme
        credit_mapping = {
            'yearly': 500,
            'monthly': 250,
            'weekly': 50
        }

        subscription_type = user_data['subscription_type']
        new_credits = credit_mapping.get(subscription_type.lower())
        
        if new_credits is None:
            return jsonify({
                "error": "Geçersiz abonelik türü",
                "status": False
            }), 400

        # Verileri güncelle
        update_data = {
            'credits': new_credits,
            'last_token_renewal_time': latest_purchase_date,  # ön yüzden gelen değeri kullan
            'subscription_expiration': subscription_expiration,  # ön yüzden gelen değeri kullan
            'is_premium': True
        }

        update_response = supabase.table('USER').update(update_data).eq('device_id', device_id).execute()

        return jsonify({
            "message": "Premium abonelik başarıyla yenilendi",
            "status": True,
            "data": {
                "new_credits": new_credits,
                "renewal_time": latest_purchase_date,
                "next_renewal_date": subscription_expiration,
                "subscription_type": subscription_type
            }
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": False
        }), 500