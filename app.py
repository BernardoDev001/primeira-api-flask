from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configurações
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tarefas.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "sua-chave-secreta-aqui"  # troque em produção!

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ==================== MODELOS ====================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    concluida = db.Column(db.Boolean, default=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "concluida": self.concluida
        }

with app.app_context():
    db.create_all()

# ==================== AUTENTICAÇÃO ====================

# POST — cadastrar usuário
@app.route("/cadastro", methods=["POST"])
def cadastro():
    dados = request.get_json()
    if Usuario.query.filter_by(email=dados["email"]).first():
        return jsonify({"erro": "Email já cadastrado"}), 400

    senha_hash = generate_password_hash(dados["senha"])
    novo_usuario = Usuario(email=dados["email"], senha=senha_hash)
    db.session.add(novo_usuario)
    db.session.commit()
    return jsonify({"mensagem": "Usuário criado com sucesso"}), 201

# POST — login
@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json()
    usuario = Usuario.query.filter_by(email=dados["email"]).first()

    if not usuario or not check_password_hash(usuario.senha, dados["senha"]):
        return jsonify({"erro": "Email ou senha inválidos"}), 401

    token = create_access_token(identity=str(usuario.id))
    return jsonify({"token": token}), 200

# ==================== TAREFAS (protegidas) ====================

# GET — listar tarefas do usuário logado
@app.route("/tarefas", methods=["GET"])
@jwt_required()
def listar_tarefas():
    usuario_id = get_jwt_identity()
    tarefas = Tarefa.query.filter_by(usuario_id=usuario_id).all()
    return jsonify([t.to_dict() for t in tarefas]), 200

# POST — criar tarefa
@app.route("/tarefas", methods=["POST"])
@jwt_required()
def criar_tarefa():
    usuario_id = get_jwt_identity()
    dados = request.get_json()
    nova_tarefa = Tarefa(titulo=dados["titulo"], usuario_id=usuario_id)
    db.session.add(nova_tarefa)
    db.session.commit()
    return jsonify(nova_tarefa.to_dict()), 201

# PUT — concluir tarefa
@app.route("/tarefas/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar_tarefa(id):
    usuario_id = get_jwt_identity()
    tarefa = Tarefa.query.filter_by(id=id, usuario_id=usuario_id).first()
    if not tarefa:
        return jsonify({"erro": "Tarefa não encontrada"}), 404
    tarefa.concluida = True
    db.session.commit()
    return jsonify(tarefa.to_dict()), 200

# DELETE — deletar tarefa
@app.route("/tarefas/<int:id>", methods=["DELETE"])
@jwt_required()
def deletar_tarefa(id):
    usuario_id = get_jwt_identity()
    tarefa = Tarefa.query.filter_by(id=id, usuario_id=usuario_id).first()
    if not tarefa:
        return jsonify({"erro": "Tarefa não encontrada"}), 404
    db.session.delete(tarefa)
    db.session.commit()
    return jsonify({"mensagem": "Tarefa deletada"}), 200

if __name__ == "__main__":
    app.run(debug=True)
