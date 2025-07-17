#!/usr/bin/env python3
"""
Script de test pour les nouvelles APIs des routines
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Changez pour votre URL de production
LOGIN_DATA = {
    "username": "admin",
    "password": "admin123"
}

def test_login():
    """Test de connexion"""
    print("🔐 Test de connexion...")
    response = requests.post(f"{BASE_URL}/login", data=LOGIN_DATA)
    if response.status_code == 200:
        print("✅ Connexion réussie")
        return response.cookies
    else:
        print(f"❌ Échec de connexion: {response.status_code}")
        return None

def test_dates_disponibles(cookies, formulaire_id=4):
    """Test de l'API des dates disponibles"""
    print(f"\n📅 Test des dates disponibles pour le formulaire {formulaire_id}...")
    response = requests.get(f"{BASE_URL}/api/routines/dates-disponibles/{formulaire_id}", cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Dates disponibles: {data.get('dates', [])}")
        return data.get('dates', [])
    else:
        print(f"❌ Erreur: {response.status_code} - {response.text}")
        return []

def test_reponses_formulaire_date(cookies, formulaire_id=4, date="2025-07-15"):
    """Test de l'API des réponses par formulaire et date"""
    print(f"\n📋 Test des réponses pour le formulaire {formulaire_id} à la date {date}...")
    response = requests.get(f"{BASE_URL}/api/routines/reponses/{formulaire_id}/{date}", cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        reponses = data.get('reponses', [])
        print(f"✅ {len(reponses)} réponses trouvées")
        
        # Afficher quelques détails
        for reponse in reponses[:3]:  # Afficher les 3 premières
            print(f"  - Question {reponse['id_question']}: {reponse['reponse']}")
        
        return reponses
    else:
        print(f"❌ Erreur: {response.status_code} - {response.text}")
        return []

def test_formulaires():
    """Test de l'API des formulaires"""
    print(f"\n📋 Test des formulaires...")
    response = requests.get(f"{BASE_URL}/api/routines/formulaires", cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {len(data)} formulaires trouvés")
        for formulaire in data:
            print(f"  - ID: {formulaire['id']}, Nom: {formulaire['nom']}")
        return data
    else:
        print(f"❌ Erreur: {response.status_code} - {response.text}")
        return []

if __name__ == "__main__":
    print("🧪 TESTS DES APIS ROUTINES")
    print("=" * 50)
    
    # Test de connexion
    cookies = test_login()
    if not cookies:
        print("❌ Impossible de continuer sans connexion")
        exit(1)
    
    # Test des formulaires
    formulaires = test_formulaires()
    
    # Test des dates disponibles
    dates = test_dates_disponibles(cookies)
    
    # Test des réponses si des dates sont disponibles
    if dates:
        test_reponses_formulaire_date(cookies, date=dates[0])
    else:
        print("\n⚠️ Aucune date disponible pour tester les réponses")
    
    print("\n" + "=" * 50)
    print("✅ TESTS TERMINÉS") 