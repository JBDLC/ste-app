#!/usr/bin/env python3
"""
Script de diagnostic pour les routines
Vérifie les données dans la base et identifie les problèmes
"""

import os
import sys
from datetime import datetime, date

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, FormulaireRoutine, QuestionRoutine, ReponseRoutine, User

def diagnostic_routines():
    """Diagnostic complet des routines"""
    print("🔍 DIAGNOSTIC DES ROUTINES")
    print("=" * 50)
    
    with app.app_context():
        # 1. Vérifier les formulaires
        print("\n📋 FORMULAIRES:")
        formulaires = FormulaireRoutine.query.all()
        print(f"Nombre de formulaires: {len(formulaires)}")
        for f in formulaires:
            print(f"  - ID: {f.id}, Nom: {f.nom}")
        
        # 2. Vérifier les questions
        print("\n❓ QUESTIONS:")
        questions = QuestionRoutine.query.all()
        print(f"Nombre total de questions: {len(questions)}")
        
        # Grouper par formulaire
        questions_par_formulaire = {}
        for q in questions:
            if q.formulaire_id not in questions_par_formulaire:
                questions_par_formulaire[q.formulaire_id] = []
            questions_par_formulaire[q.formulaire_id].append(q)
        
        for formulaire_id, qs in questions_par_formulaire.items():
            formulaire = FormulaireRoutine.query.get(formulaire_id)
            print(f"  - {formulaire.nom if formulaire else f'Formulaire {formulaire_id}'}: {len(qs)} questions")
        
        # 3. Vérifier les réponses
        print("\n✅ RÉPONSES:")
        reponses = ReponseRoutine.query.all()
        print(f"Nombre total de réponses: {len(reponses)}")
        
        # Grouper par date
        reponses_par_date = {}
        for r in reponses:
            date_str = r.date_creation.strftime('%Y-%m-%d')
            if date_str not in reponses_par_date:
                reponses_par_date[date_str] = []
            reponses_par_date[date_str].append(r)
        
        print("Réponses par date:")
        for date_str, rs in sorted(reponses_par_date.items()):
            print(f"  - {date_str}: {len(rs)} réponses")
        
        # 4. Vérifier les réponses d'aujourd'hui
        today = date.today()
        reponses_aujourdhui = ReponseRoutine.query.filter_by(date_creation=today).all()
        print(f"\n📅 RÉPONSES AUJOURD'HUI ({today}):")
        print(f"Nombre: {len(reponses_aujourdhui)}")
        
        # Grouper par formulaire
        reponses_par_formulaire = {}
        for r in reponses_aujourdhui:
            if r.formulaire_id not in reponses_par_formulaire:
                reponses_par_formulaire[r.formulaire_id] = []
            reponses_par_formulaire[r.formulaire_id].append(r)
        
        for formulaire_id, rs in reponses_par_formulaire.items():
            formulaire = FormulaireRoutine.query.get(formulaire_id)
            print(f"  - {formulaire.nom if formulaire else f'Formulaire {formulaire_id}'}: {len(rs)} réponses")
        
        # 5. Test de la route API
        print("\n🔧 TEST DE LA ROUTE API:")
        try:
            # Simuler une requête à l'API
            from flask import request
            with app.test_request_context():
                # Test de la route /api/routines/reponses/<date>
                date_str = today.strftime('%Y-%m-%d')
                print(f"Test de la route /api/routines/reponses/{date_str}")
                
                # Récupérer les réponses via la requête SQL directe
                reponses_api = db.session.query(ReponseRoutine, QuestionRoutine, FormulaireRoutine).join(
                    QuestionRoutine, ReponseRoutine.question_id == QuestionRoutine.id
                ).join(
                    FormulaireRoutine, ReponseRoutine.formulaire_id == FormulaireRoutine.id
                ).filter(
                    ReponseRoutine.date_creation == today
                ).order_by(ReponseRoutine.heure_creation.desc()).all()
                
                print(f"Résultats de la requête API: {len(reponses_api)} réponses")
                
                for reponse, question, formulaire in reponses_api:
                    print(f"  - Formulaire: {formulaire.nom} (ID: {formulaire.id})")
                    print(f"    Question: {question.id_question} - {question.question}")
                    print(f"    Réponse: {reponse.reponse}")
                    print(f"    Commentaire: {reponse.commentaire}")
                    print(f"    Heure: {reponse.heure_creation}")
                    print()
                
        except Exception as e:
            print(f"Erreur lors du test API: {e}")
        
        # 6. Vérifier les utilisateurs
        print("\n👥 UTILISATEURS:")
        users = User.query.all()
        print(f"Nombre d'utilisateurs: {len(users)}")
        for user in users:
            print(f"  - ID: {user.id}, Username: {user.username}, Role: {user.role}")
        
        print("\n" + "=" * 50)
        print("✅ DIAGNOSTIC TERMINÉ")

if __name__ == "__main__":
    diagnostic_routines() 