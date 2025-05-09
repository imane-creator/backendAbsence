from flask import Blueprint, request, jsonify, session
from app import mysql
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return jsonify({"message": "Bienvenue sur l'API Flask!"})


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email et mot de passe sont requis"}), 400

        email = data['email']
        password = data['password']

        # Vérification administrateur
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, password FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
            session['user_id'] = user[0]
            return jsonify({
                "message": "Connexion réussie",
                "user_id": user[0],
                "role": "admin"
            }), 200

        # Vérification professeur
        cursor.execute("SELECT id, mot_de_passe FROM professeurs WHERE email=%s", (email,))
        professeur = cursor.fetchone()
        cursor.close()

        if professeur and password == professeur[1]:
            session['professeur_id'] = professeur[0]
            return jsonify({
                "message": "Connexion réussie",
                "professeur_id": professeur[0],
                "role": "professor"
            }), 200

        return jsonify({"error": "Identifiants invalides"}), 401

    except Exception as e:
        print(f"Erreur lors de la connexion: {str(e)}")
        return jsonify({"error": "Erreur serveur"}), 500
    finally:
        cursor.close()


def check_admin_credentials(email, password):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, password FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
        return {"id": user[0]}
    return None


def check_professor_credentials(email, password):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, mot_de_passe FROM professeurs WHERE email=%s", (email,))
    professeur = cursor.fetchone()
    cursor.close()

    if professeur and password == professeur[1]:
        return {"id": professeur[0]}
    return None

