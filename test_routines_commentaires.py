#!/usr/bin/env python3
"""
Test pour vérifier que les commentaires ne suppriment plus les réponses précédentes
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # ou l'URL de production
LOGIN_DATA = {
    "username": "admin",
    "password": "admin123"
}

def test_routines_commentaires():
    """Test du problème des commentaires qui annulent les réponses"""
    
    print("🧪 Test des routines avec commentaires")
    print("=" * 50)
    
    # 1. Connexion
    print("1. Connexion...")
    session = requests.Session()
    login_response = session.post(f"{BASE_URL}/login", data=LOGIN_DATA)
    if login_response.status_code != 200:
        print("❌ Échec de la connexion")
        return False
    print("✅ Connexion réussie")
    
    # 2. Récupérer un formulaire
    print("\n2. Récupération d'un formulaire...")
    formulaires_response = session.get(f"{BASE_URL}/api/routines/formulaires")
    if formulaires_response.status_code != 200:
        print("❌ Impossible de récupérer les formulaires")
        return False
    
    formulaires = formulaires_response.json()
    if not formulaires:
        print("❌ Aucun formulaire trouvé")
        return False
    
    formulaire_id = formulaires[0]['id']
    print(f"✅ Formulaire sélectionné: {formulaires[0]['nom']} (ID: {formulaire_id})")
    
    # 3. Récupérer les questions
    print("\n3. Récupération des questions...")
    questions_response = session.get(f"{BASE_URL}/api/routines/formulaires/{formulaire_id}/questions")
    if questions_response.status_code != 200:
        print("❌ Impossible de récupérer les questions")
        return False
    
    questions = questions_response.json()
    if not questions:
        print("❌ Aucune question trouvée")
        return False
    
    question_id = questions[0]['id']
    print(f"✅ Question sélectionnée: {questions[0]['question'][:50]}... (ID: {question_id})")
    
    # 4. Ajouter une première réponse
    print("\n4. Ajout d'une première réponse...")
    reponse1_data = {
        'formulaireId': formulaire_id,
        'questionId': question_id,
        'reponse': 'Fait',
        'commentaire': ''
    }
    
    reponse1_response = session.post(f"{BASE_URL}/api/routines/reponses", data=reponse1_data)
    if reponse1_response.status_code != 200:
        print("❌ Impossible d'ajouter la première réponse")
        return False
    
    reponse1_result = reponse1_response.json()
    if 'error' in reponse1_result:
        print(f"❌ Erreur lors de l'ajout de la première réponse: {reponse1_result['error']}")
        return False
    
    reponse_id = reponse1_result.get('id')
    print(f"✅ Première réponse ajoutée (ID: {reponse_id})")
    
    # 5. Vérifier que la réponse existe
    print("\n5. Vérification de la première réponse...")
    today = datetime.now().strftime('%Y-%m-%d')
    reponses_response = session.get(f"{BASE_URL}/api/routines/reponses/{today}")
    if reponses_response.status_code != 200:
        print("❌ Impossible de récupérer les réponses")
        return False
    
    reponses = reponses_response.json()
    reponse_trouvee = None
    for rep in reponses:
        if rep['question_id'] == question_id and rep['formulaire_id'] == formulaire_id:
            reponse_trouvee = rep
            break
    
    if not reponse_trouvee:
        print("❌ La première réponse n'a pas été trouvée")
        return False
    
    print(f"✅ Première réponse trouvée: {reponse_trouvee['reponse']}")
    
    # 6. Ajouter un commentaire à la réponse
    print("\n6. Ajout d'un commentaire...")
    commentaire_data = {
        'reponse': 'Fait',
        'commentaire': 'Test de commentaire'
    }
    
    commentaire_response = session.put(f"{BASE_URL}/api/routines/reponses/{reponse_id}", data=commentaire_data)
    if commentaire_response.status_code != 200:
        print("❌ Impossible d'ajouter le commentaire")
        return False
    
    commentaire_result = commentaire_response.json()
    if 'error' in commentaire_result:
        print(f"❌ Erreur lors de l'ajout du commentaire: {commentaire_result['error']}")
        return False
    
    print("✅ Commentaire ajouté")
    
    # 7. Vérifier que la réponse existe toujours
    print("\n7. Vérification que la réponse existe toujours...")
    reponses_response2 = session.get(f"{BASE_URL}/api/routines/reponses/{today}")
    if reponses_response2.status_code != 200:
        print("❌ Impossible de récupérer les réponses après commentaire")
        return False
    
    reponses2 = reponses_response2.json()
    reponse_trouvee2 = None
    for rep in reponses2:
        if rep['question_id'] == question_id and rep['formulaire_id'] == formulaire_id:
            reponse_trouvee2 = rep
            break
    
    if not reponse_trouvee2:
        print("❌ La réponse a disparu après l'ajout du commentaire!")
        return False
    
    if reponse_trouvee2['commentaire'] != 'Test de commentaire':
        print(f"❌ Le commentaire n'a pas été sauvegardé: {reponse_trouvee2['commentaire']}")
        return False
    
    print(f"✅ Réponse toujours présente avec commentaire: {reponse_trouvee2['commentaire']}")
    
    # 8. Nettoyer - supprimer la réponse de test
    print("\n8. Nettoyage...")
    delete_response = session.delete(f"{BASE_URL}/api/routines/reponses/{reponse_id}")
    if delete_response.status_code == 200:
        print("✅ Réponse de test supprimée")
    else:
        print("⚠️ Impossible de supprimer la réponse de test")
    
    print("\n🎉 Test terminé avec succès!")
    print("✅ Le problème des commentaires qui annulent les réponses est résolu")
    return True

if __name__ == "__main__":
    try:
        success = test_routines_commentaires()
        if success:
            print("\n✅ Tous les tests sont passés!")
        else:
            print("\n❌ Certains tests ont échoué")
    except Exception as e:
        print(f"\n❌ Erreur lors du test: {e}") 