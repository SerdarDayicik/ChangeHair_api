from flask import Flask
from flask_cors import CORS


#controller importları
from controllers.session_controller import session_bp
from controllers.changeHair_Controller import model_bp





app = Flask(__name__)
CORS(app)





# Controller'lar
app.register_blueprint(session_bp, url_prefix='/session')
app.register_blueprint(model_bp, url_prefix='/model')



@app.route('/')
def home():
    return {"message": "Merhaba, API'ye hoşgeldin!"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
