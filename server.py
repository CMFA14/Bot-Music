from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__, static_folder='web')
CORS(app)

FILE_STATUS = "status.json"
FILE_COMANDOS = "comandos.json"

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('web', path)

@app.route('/api/status', methods=['GET'])
def get_status():
    if not os.path.exists(FILE_STATUS):
        return jsonify({"tocando": "Bot Offline", "fila": [], "status": "Desconectado"})
    try:
        with open(FILE_STATUS, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"tocando": "Carregando...", "fila": [], "status": "..."})

@app.route('/api/comando', methods=['POST'])
def enviar_comando():
    dados_recebidos = request.json
    action = dados_recebidos.get('action')
    data = dados_recebidos.get('data')
    
    cmd = {"action": action, "data": data}
    with open(FILE_COMANDOS, "w", encoding="utf-8") as f:
        json.dump(cmd, f)
    
    return jsonify({"status": "sucesso", "mensagem": f"Comando {action} enviado"})

if __name__ == '__main__':
    # Roda na porta 80 para domínio, ou 5000 para teste local
    app.run(host='0.0.0.0', port=5000, debug=True)
