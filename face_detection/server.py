import asyncio
import websockets
import cv2
import numpy as np
import io
from PIL import Image
import logging
import json
import os
from app import mysql
from app import create_app

app = create_app()

logging.basicConfig(level=logging.DEBUG)

# Chargement du classificateur Haar pour la détection des visages
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Création du reconnaisseur LBPH
recognizer = cv2.face.LBPHFaceRecognizer_create()

# Dictionnaire pour mapper les labels aux noms des étudiants
label_to_name = {}

# Fonction pour entraîner le modèle LBPH
def train_lbph():
    images = []
    labels = []
    label_id = 0
    folderPath = 'Images'

    for studentFolder in os.listdir(folderPath):
        studentPath = os.path.join(folderPath, studentFolder)
        if not os.path.isdir(studentPath):
            continue
        student_name = studentFolder.replace("_", " ")
        label_to_name[label_id] = student_name

        for imgName in os.listdir(studentPath):
            imgPath = os.path.join(studentPath, imgName)
            img = cv2.imread(imgPath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            faces = face_cascade.detectMultiScale(img, scaleFactor=1.2, minNeighbors=5)
            for (x, y, w, h) in faces:
                face = img[y:y + h, x:x + w]
                face = cv2.resize(face, (100, 100))
                images.append(face)
                labels.append(label_id)
        label_id += 1

    if images:
        recognizer.train(images, np.array(labels))
        logging.info("Modèle LBPH entraîné avec succès")
    else:
        logging.error("Aucune image valide pour l'entraînement")
        exit(1)

# Entraîner le modèle au démarrage
train_lbph()

# Fonction pour insérer les présences dans la base de données
def insert_presence(seance_id, etudiant_nom):
    with app.app_context():
        try:
            cursor = mysql.connection.cursor()
            query = "INSERT IGNORE INTO presence (seance_id, etudiant_nom) VALUES (%s, %s)"
            cursor.execute(query, (seance_id, etudiant_nom))
            mysql.connection.commit()
            cursor.close()
            logging.info(f"Présence enregistrée pour {etudiant_nom} dans la séance {seance_id}")
        except Exception as e:
            logging.error(f"Erreur lors de l'insertion : {e}")
            mysql.connection.rollback()

async def process_image(websocket, path):
    logging.info("Client connecté")
    try:
        while True:
            # Étape 1 : Recevoir le message JSON avec seance_id
            json_message = await websocket.recv()
            if not isinstance(json_message, str):
                logging.error("Message attendu : JSON string")
                continue

            try:
                data = json.loads(json_message)
                seance_id = data['seance_id']
            except Exception as e:
                logging.error(f"JSON invalide : {e}")
                continue

            # Étape 2 : Recevoir les bytes de l'image
            image_message = await websocket.recv()
            if not isinstance(image_message, bytes):
                logging.error("Message attendu : données binaires de l'image")
                continue

            logging.info(f"Image reçue pour la séance {seance_id}, taille : {len(image_message)} bytes")


            # Traitement de l'image (votre logique existante)
            try:
                image = Image.open(io.BytesIO(image_message))
            except Exception as e:
                logging.error(f"Erreur lors de l'ouverture de l'image : {e}")
                continue

            img = np.array(image)
            imgs = cv2.resize(img, (0, 0), fx=0.3, fy=0.3)
            gray = cv2.cvtColor(imgs, cv2.COLOR_RGB2GRAY)

            # Détection des visages
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            detections = []
            detected_ids = set()

            # Reconnaissance faciale
            for (x, y, w, h) in faces:
                face = gray[y:y + h, x:x + w]
                face = cv2.resize(face, (100, 100))
                label, confidence = recognizer.predict(face)
                if confidence < 100:  # Seuil de confiance
                    student_id = label_to_name.get(label, "Inconnu")
                    if student_id != "Inconnu":
                        detected_ids.add(student_id)
                        detections.append({
                            "id": student_id,
                            "left": int(x),
                            "top": int(y),
                            "right": int(x + w),
                            "bottom": int(y + h)
                        })

            # Enregistrer les présences
            for student_id in detected_ids:
                insert_presence(seance_id, student_id)

            # Réponse au client
            image_size = {"width": int(imgs.shape[1]), "height": int(imgs.shape[0])}
            response = {"detections": detections, "image_size": image_size}
            await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosed:
        logging.info("Client déconnecté")
    except Exception as e:
        logging.error(f"Erreur inattendue : {e}")

start_server = websockets.serve(process_image, "0.0.0.0", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()