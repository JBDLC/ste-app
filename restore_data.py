#!/usr/bin/env python3
"""
Script pour restaurer les données depuis la base SQLite locale vers PostgreSQL sur Render
"""

import os
import sys
import sqlite3
from datetime import datetime

# Ajouter le répertoire courant au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, Site, TypeReleve, Releve, PhotoReleve, FormulaireRoutine, QuestionRoutine, ReponseRoutine, EmailConfig
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def restore_from_local_db():
    """Restaurer les données depuis la base SQLite locale"""
    print("🔄 RESTAURATION DES DONNÉES DEPUIS LA BASE LOCALE")
    print("=" * 60)
    
    # Chemin vers la base SQLite locale
    local_db_path = 'instance/ste_releve.db'
    
    if not os.path.exists(local_db_path):
        print(f"❌ Base locale non trouvée: {local_db_path}")
        return
    
    print(f"📁 Base locale trouvée: {local_db_path}")
    
    # Connexion à la base SQLite locale
    local_conn = sqlite3.connect(local_db_path)
    local_cursor = local_conn.cursor()
    
    with app.app_context():
        try:
            # 1. Vérifier que la base PostgreSQL est prête
            print("\n1️⃣ VÉRIFICATION DE LA BASE POSTGRESQL")
            print("-" * 40)
            
            # Vérifier que les sites existent
            sites = Site.query.all()
            if not sites:
                print("❌ Aucun site trouvé dans PostgreSQL")
                print("🔧 Création des sites...")
                
                smp = Site(nom='SMP', description='Station de traitement des eaux SMP')
                lpz = Site(nom='LPZ', description='Station de traitement des eaux LPZ')
                db.session.add(smp)
                db.session.add(lpz)
                db.session.commit()
                print("✅ Sites créés")
            else:
                print(f"✅ {len(sites)} sites trouvés")
            
            # 2. Restaurer les types de relevés
            print("\n2️⃣ RESTAURATION DES TYPES DE RELEVÉS")
            print("-" * 40)
            
            # Vérifier les types existants dans PostgreSQL
            existing_types = TypeReleve.query.all()
            if not existing_types:
                print("🔧 Création des types de relevés...")
                
                # Récupérer les types depuis SQLite
                local_cursor.execute("SELECT nom, site_id, type_mesure, unite, frequence, jour_specifique FROM type_releve")
                types_data = local_cursor.fetchall()
                
                for nom, site_id, type_mesure, unite, frequence, jour_specifique in types_data:
                    tr = TypeReleve()
                    tr.nom = nom
                    tr.site_id = site_id
                    tr.type_mesure = type_mesure
                    tr.unite = unite
                    tr.frequence = frequence
                    tr.jour_specifique = jour_specifique
                    db.session.add(tr)
                
                db.session.commit()
                print(f"✅ {len(types_data)} types de relevés restaurés")
            else:
                print(f"✅ {len(existing_types)} types de relevés déjà existants")
            
            # 3. Restaurer les relevés
            print("\n3️⃣ RESTAURATION DES RELEVÉS")
            print("-" * 40)
            
            # Compter les relevés existants
            existing_releves = Releve.query.count()
            if existing_releves == 0:
                print("🔧 Restauration des relevés...")
                
                # Récupérer les relevés depuis SQLite
                local_cursor.execute("""
                    SELECT date, type_releve_id, valeur, utilisateur_id, commentaire, created_at 
                    FROM releve 
                    ORDER BY date DESC
                """)
                releves_data = local_cursor.fetchall()
                
                for date_str, type_releve_id, valeur, utilisateur_id, commentaire, created_at in releves_data:
                    # Convertir la date
                    if isinstance(date_str, str):
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        date_obj = date_str
                    
                    releve = Releve()
                    releve.date = date_obj
                    releve.type_releve_id = type_releve_id
                    releve.valeur = valeur
                    releve.utilisateur_id = utilisateur_id
                    releve.commentaire = commentaire
                    if created_at:
                        releve.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    db.session.add(releve)
                
                db.session.commit()
                print(f"✅ {len(releves_data)} relevés restaurés")
            else:
                print(f"⚠️ {existing_releves} relevés déjà existants, pas de restauration")
            
            # 4. Restaurer les photos
            print("\n4️⃣ RESTAURATION DES PHOTOS")
            print("-" * 40)
            
            # Compter les photos existantes
            existing_photos = PhotoReleve.query.count()
            if existing_photos == 0:
                print("🔧 Restauration des photos...")
                
                # Récupérer les photos depuis SQLite
                local_cursor.execute("""
                    SELECT date, site_id, nom_debitmetre, fichier_photo, utilisateur_id, commentaire, session_id, created_at 
                    FROM photo_releve 
                    ORDER BY date DESC
                """)
                photos_data = local_cursor.fetchall()
                
                for date_str, site_id, nom_debitmetre, fichier_photo, utilisateur_id, commentaire, session_id, created_at in photos_data:
                    # Convertir la date
                    if isinstance(date_str, str):
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        date_obj = date_str
                    
                    photo = PhotoReleve()
                    photo.date = date_obj
                    photo.site_id = site_id
                    photo.nom_debitmetre = nom_debitmetre
                    photo.fichier_photo = fichier_photo
                    photo.utilisateur_id = utilisateur_id
                    photo.commentaire = commentaire
                    photo.session_id = session_id
                    if created_at:
                        photo.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    db.session.add(photo)
                
                db.session.commit()
                print(f"✅ {len(photos_data)} photos restaurées")
            else:
                print(f"⚠️ {existing_photos} photos déjà existantes, pas de restauration")
            
            # 5. Restaurer les routines
            print("\n5️⃣ RESTAURATION DES ROUTINES")
            print("-" * 40)
            
            # Restaurer les formulaires de routines
            existing_formulaires = FormulaireRoutine.query.count()
            if existing_formulaires == 0:
                print("🔧 Restauration des formulaires de routines...")
                
                local_cursor.execute("SELECT nom, created_at FROM formulaire_routine")
                formulaires_data = local_cursor.fetchall()
                
                for nom, created_at in formulaires_data:
                    formulaire = FormulaireRoutine()
                    formulaire.nom = nom
                    if created_at:
                        formulaire.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    db.session.add(formulaire)
                
                db.session.commit()
                print(f"✅ {len(formulaires_data)} formulaires de routines restaurés")
            else:
                print(f"⚠️ {existing_formulaires} formulaires déjà existants")
            
            # 6. Statistiques finales
            print("\n6️⃣ STATISTIQUES FINALES")
            print("-" * 40)
            
            total_releves = Releve.query.count()
            total_photos = PhotoReleve.query.count()
            total_types = TypeReleve.query.count()
            total_sites = Site.query.count()
            
            print(f"📊 Statistiques de la base PostgreSQL:")
            print(f"   - Sites: {total_sites}")
            print(f"   - Types de relevés: {total_types}")
            print(f"   - Relevés: {total_releves}")
            print(f"   - Photos: {total_photos}")
            
            print("\n" + "=" * 60)
            print("🎉 RESTAURATION TERMINÉE AVEC SUCCÈS!")
            print("=" * 60)
            print("✅ Vos données ont été restaurées depuis la base locale")
            print("🔗 Vous pouvez maintenant voir vos relevés dans l'application")
            
        except Exception as e:
            print(f"❌ ERREUR lors de la restauration: {e}")
            db.session.rollback()
            raise
        finally:
            local_conn.close()

if __name__ == '__main__':
    restore_from_local_db() 