import asyncio
import websockets
import cv2
import numpy as np
from supabase import create_client, Client
import io
from PIL import Image
from fpdf import FPDF
import logging
import json
import time
import os

logging.basicConfig(level=logging.DEBUG)

# Connexion Supabase (non utilisé dans le code actuel)
url = "https://vtfqmnbbuiicqhgmdbje.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0ZnFtbmJidWlpY3FoZ21kYmplIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU2NjMyOTEsImV4cCI6MjA2MTIzOTI5MX0.n8om43B8BQ452TheJbgKDGz_8zPASP1zTIoVfwlrGsA"
supabase: Client = create_client(url, key)

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


async def process_image(websocket, path):
    logging.info("Client connecté")
    detected_ids = set()
    try:
        async for message in websocket:
            logging.info(f"Image reçue, taille : {len(message)} bytes")
            with open("received_image.jpg", "wb") as f:
                f.write(message)
            logging.info("Image sauvegardée pour inspection : received_image.jpg")

            try:
                image = Image.open(io.BytesIO(message))
            except Exception as e:
                logging.error(f"Erreur lors de l'ouverture de l'image : {e}")
                continue

            img = np.array(image)
            logging.info(f"Image shape: {img.shape}")
            imgs = cv2.resize(img, (0, 0), fx=0.3, fy=0.3)
            gray = cv2.cvtColor(imgs, cv2.COLOR_RGB2GRAY)
            logging.info(f"Resized image shape: {imgs.shape}")

            start_time = time.time()
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            detection_time = time.time() - start_time
            logging.info(f"Temps de détection : {detection_time} secondes")

            detections = []
            start_time = time.time()
            for (x, y, w, h) in faces:
                face = gray[y:y + h, x:x + w]
                face = cv2.resize(face, (100, 100))
                label, confidence = recognizer.predict(face)
                if confidence < 100:  # Seuil de confiance
                    student_id = label_to_name.get(label, "Inconnu")
                    detected_ids.add(student_id)
                    detections.append({
                        "id": student_id,
                        "left": int(x),
                        "top": int(y),
                        "right": int(x + w),
                        "bottom": int(y + h)
                    })
            recognition_time = time.time() - start_time
            logging.info(f"Temps de reconnaissance : {recognition_time} secondes")
            logging.info(f"Temps total : {detection_time + recognition_time} secondes")

            image_size = {
                "width": int(imgs.shape[1]),
                "height": int(imgs.shape[0])
            }

            response = {
                "detections": detections,
                "image_size": image_size
            }
            await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosed:
        logging.info("Client déconnecté")
    except Exception as e:
        logging.error(f"Erreur: {e}")
    finally:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Liste des étudiants présents", ln=True, align='C')
        for student_id in detected_ids:
            pdf.cell(200, 10, txt=f"{student_id}", ln=True, align='L')
        pdf.output("students_detected.pdf")
        logging.info("PDF généré : students_detected.pdf")


start_server = websockets.serve(process_image, "0.0.0.0", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()