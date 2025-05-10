from flask import Blueprint, request, jsonify
from app import mysql

seance_bp = Blueprint('seance', __name__)

@seance_bp.route('/seance/<int:seance_id>', methods=['DELETE'])
def delete_seance(seance_id):
    cursor = mysql.connection.cursor()

    # Vérifier si la séance existe
    cursor.execute("SELECT * FROM seanceprofesseur WHERE id = %s", (seance_id,))
    seance = cursor.fetchone()

    if not seance:
        cursor.close()
        return jsonify({'error': 'Séance non trouvée'}), 404

    # Supprimer la séance
    cursor.execute("DELETE FROM seanceprofesseur WHERE id = %s", (seance_id,))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'Séance supprimée avec succès'}), 200

@seance_bp.route('/seance', methods=['POST'])
def ajouter_seance_professeur():
    data = request.get_json()

    professeur_id = data.get('professeur_id')
    module_id = data.get('module_id')
    salle = data.get('salle')
    date = data.get('date')  # format: 'YYYY-MM-DD'
    heure_debut = data.get('heure_debut')  # format: 'HH:MM:SS'
    heure_fin = data.get('heure_fin')      # format: 'HH:MM:SS'

    if not all([professeur_id, module_id, salle, date, heure_debut, heure_fin]):
        return jsonify({'error': 'Tous les champs sont requis'}), 400

    cursor = mysql.connection.cursor()

    # Vérifier si la salle est occupée
    query_salle = """
        SELECT 1 FROM seanceprofesseur
        WHERE salle = %s AND date = %s AND (%s < heure_fin AND %s > heure_debut)
    """
    cursor.execute(query_salle, (salle, date, heure_debut, heure_fin))
    salle_occupee = cursor.fetchone()

    if salle_occupee:
        cursor.close()
        return jsonify({'error': 'La salle est déjà occupée pendant cet horaire'}), 409

    # Vérifier si le professeur est déjà occupé à cet horaire
    query_professeur = """
        SELECT 1 FROM seanceprofesseur
        WHERE professeur_id = %s AND date = %s AND (%s < heure_fin AND %s > heure_debut)
    """
    cursor.execute(query_professeur, (professeur_id, date, heure_debut, heure_fin))
    prof_occupe = cursor.fetchone()

    if prof_occupe:
        cursor.close()
        return jsonify({'error': 'Le professeur est déjà occupé pendant cet horaire'}), 409

    # Insertion de la séance
    query_insert = """
        INSERT INTO seanceprofesseur (professeur_id, module_id, salle, date, heure_debut, heure_fin)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query_insert, (professeur_id, module_id, salle, date, heure_debut, heure_fin))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'message': 'Séance ajoutée avec succès'}), 201

@seance_bp.route('/seance', methods=['GET'])
def get_all_seances():
    cursor = mysql.connection.cursor()

    # Requête SQL pour récupérer toutes les séances
    query = """
        SELECT sp.id, sp.professeur_id, sp.module_id, sp.salle, sp.date, sp.heure_debut, sp.heure_fin,
               p.nom AS nom_professeur, m.nom AS nom_module
        FROM seanceprofesseur sp
        JOIN professeurs p ON sp.professeur_id = p.id
        JOIN modules m ON sp.module_id = m.id
        ORDER BY sp.date DESC, sp.heure_debut ASC
    """
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()

    # Transformer le résultat en format JSON
    seances = []
    for row in result:
        seances.append({
            'id': row[0],
            'professeur_id': row[1],
            'module_id': row[2],
            'salle': row[3],
            'date': row[4].strftime('%Y-%m-%d'),
            'heure_debut': str(row[5]).split('.')[0],  # supprime les microsecondes
            'heure_fin': str(row[6]).split('.')[0],    # supprime les microsecondes
            'professeur': row[7],
            'module': row[8]
        })

    return jsonify(seances), 200

@seance_bp.route('/seance/<int:seance_id>/etudiants_presents', methods=['GET'])
def get_etudiants_presents(seance_id):
    cursor = mysql.connection.cursor()
    query = "SELECT etudiant_nom FROM presence WHERE seance_id = %s"
    cursor.execute(query, (seance_id,))
    result = cursor.fetchall()
    cursor.close()
    etudiants = [row[0] for row in result]
    return jsonify(etudiants), 200