from flask import Blueprint, request, jsonify
from app import mysql

professeur_bp = Blueprint('professeur', __name__)


@professeur_bp.route('/professeurs', methods=['POST'])
def ajouter_prof():
    data = request.get_json()
    nom = data.get('nom')
    email = data.get('email')
    filiere_id = data.get('filiere_id')
    module_id = data.get('module_id')

    if not nom or not email or not filiere_id or not module_id:
        return jsonify({"error": "Tous les champs sont requis"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("""
                   INSERT INTO professeurs (nom, email, filiere_id, module_id)
                   VALUES (%s, %s, %s, %s)
                   """, (nom, email, filiere_id, module_id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({"message": "Professeur ajouté avec succès"})


@professeur_bp.route('/professeurs', methods=['GET'])
def get_professeurs_par_filiere_et_module():
    filiere_id = request.args.get('filiere_id')
    module_id = request.args.get('module_id')

    if not filiere_id or not module_id:
        return jsonify({"error": "filiere_id et module_id sont requis"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("""
                   SELECT id, nom, email
                   FROM professeurs
                   WHERE filiere_id = %s
                     AND module_id = %s
                   """, (filiere_id, module_id))

    professeurs = cursor.fetchall()
    cursor.close()

    professeur_list = [{"id": p[0], "nom": p[1], "email": p[2]} for p in professeurs]
    return jsonify(professeur_list)