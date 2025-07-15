#!/usr/bin/env python3
"""
Script pour forcer la réinitialisation complète de la base de données sur Render
ATTENTION: Ce script supprime toutes les données existantes!
"""

import os
import sys
from datetime import datetime

# Ajouter le répertoire courant au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, Site, TypeReleve, TypeReleve, FormulaireRoutine, EmailConfig
    from werkzeug.security import generate_password_hash
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def reset_database():
    """Réinitialisation complète de la base de données"""
    print("🚨 RÉINITIALISATION COMPLÈTE DE LA BASE DE DONNÉES")
    print("=" * 60)
    print("⚠️  ATTENTION: Toutes les données existantes seront supprimées!")
    print("=" * 60)
    
    with app.app_context():
        try:
            # 1. Supprimer toutes les tables existantes
            print("\n1️⃣ SUPPRESSION DES TABLES EXISTANTES")
            print("-" * 40)
            
            db.drop_all()
            print("✅ Toutes les tables supprimées")
            
            # 2. Recréer toutes les tables
            print("\n2️⃣ CRÉATION DES NOUVELLES TABLES")
            print("-" * 40)
            
            db.create_all()
            print("✅ Toutes les tables recréées")
            
            # 3. Créer les sites
            print("\n3️⃣ CRÉATION DES SITES")
            print("-" * 40)
            
            smp = Site(nom='SMP', description='Station de traitement des eaux SMP')
            lpz = Site(nom='LPZ', description='Station de traitement des eaux LPZ')
            db.session.add(smp)
            db.session.add(lpz)
            db.session.commit()
            print("✅ Sites SMP et LPZ créés")
            
            # 4. Créer les types de relevés pour SMP
            print("\n4️⃣ CRÉATION DES TYPES DE RELEVÉS SMP")
            print("-" * 40)
            
            types_smp = [
                ('Exhaure 1', 'totalisateur', 'm³', 'quotidien'),
                ('Exhaure 2', 'totalisateur', 'm³', 'quotidien'),
                ('Exhaure 3', 'totalisateur', 'm³', 'quotidien'),
                ('Exhaure 4', 'totalisateur', 'm³', 'quotidien'),
                ('Retour dessableur', 'totalisateur', 'm³', 'quotidien'),
                ('Retour Orage', 'totalisateur', 'm³', 'quotidien'),
                ('Rejet à l\'Arc', 'totalisateur', 'm³', 'quotidien'),
                ('Surpresseur 4 pompes', 'totalisateur', 'm³', 'quotidien'),
                ('Surpresseur 7 pompes', 'totalisateur', 'm³', 'quotidien'),
                ('Entrée STE CAB', 'totalisateur', 'm³', 'quotidien'),
                ('Alimentation CAB', 'totalisateur', 'm³', 'quotidien'),
                ('Eau potable', 'totalisateur', 'm³', 'hebdomadaire', 'lundi'),
                ('Forage', 'totalisateur', 'm³', 'quotidien'),
                ('Boue STE', 'basique', 'pressées', 'quotidien'),
                ('Boue STE CAB', 'basique', 'pressées', 'quotidien'),
                ('pH entrée', 'basique', '', 'quotidien'),
                ('pH sortie', 'basique', '', 'quotidien'),
                ('Température entrée', 'basique', '°C', 'quotidien'),
                ('Température sortie', 'basique', '°C', 'quotidien'),
                ('Conductivité sortie', 'basique', 'µS/cm', 'quotidien'),
                ('MES entrée', 'basique', 'mg/L', 'quotidien'),
                ('MES sortie', 'basique', 'mg/L', 'quotidien'),
                ('Coagulant', 'basique', 'L', 'hebdomadaire', 'lundi'),
                ('Floculant', 'basique', 'kg', 'quotidien'),
                ('CO2', 'basique', '%', 'quotidien')
            ]
            
            for nom, type_mesure, unite, frequence, *args in types_smp:
                jour_specifique = args[0] if args else None
                tr = TypeReleve()
                tr.nom = nom
                tr.site_id = smp.id
                tr.type_mesure = type_mesure
                tr.unite = unite
                tr.frequence = frequence
                tr.jour_specifique = jour_specifique
                db.session.add(tr)
            
            print(f"✅ {len(types_smp)} types de relevés SMP créés")
            
            # 5. Créer les types de relevés pour LPZ
            print("\n5️⃣ CRÉATION DES TYPES DE RELEVÉS LPZ")
            print("-" * 40)
            
            types_lpz = [
                ('Exhaure 1', 'totalisateur', 'm³', 'quotidien'),
                ('Exhaure 2', 'totalisateur', 'm³', 'quotidien'),
                ('Retour dessableur', 'totalisateur', 'm³', 'quotidien'),
                ('Surpresseur BP', 'totalisateur', 'm³', 'quotidien'),
                ('Surpresseur HP', 'totalisateur', 'm³', 'quotidien'),
                ('Rejet à l\'Arc', 'totalisateur', 'm³', 'quotidien'),
                ('Entrée STE CAB', 'totalisateur', 'm³', 'quotidien'),
                ('Alimentation CAB', 'totalisateur', 'm³', 'quotidien'),
                ('Eau de montagne', 'totalisateur', 'm³', 'quotidien'),
                ('Eau potable', 'totalisateur', 'm³', 'hebdomadaire', 'lundi'),
                ('Boue STE', 'basique', 'pressées', 'quotidien'),
                ('Boue STE CAB', 'basique', 'pressées', 'quotidien'),
                ('pH entrée', 'basique', '', 'quotidien'),
                ('pH sortie', 'basique', '', 'quotidien'),
                ('Température entrée', 'basique', '°C', 'quotidien'),
                ('Température sortie', 'basique', '°C', 'quotidien'),
                ('Conductivité sortie', 'basique', 'µS/cm', 'quotidien'),
                ('MES entrée', 'basique', 'mg/L', 'quotidien'),
                ('MES sortie', 'basique', 'mg/L', 'quotidien'),
                ('Coagulant', 'basique', 'L', 'hebdomadaire', 'lundi'),
                ('Floculant', 'basique', 'kg', 'quotidien'),
                ('CO2', 'basique', '%', 'quotidien')
            ]
            
            for nom, type_mesure, unite, frequence, *args in types_lpz:
                jour_specifique = args[0] if args else None
                tr = TypeReleve()
                tr.nom = nom
                tr.site_id = lpz.id
                tr.type_mesure = type_mesure
                tr.unite = unite
                tr.frequence = frequence
                tr.jour_specifique = jour_specifique
                db.session.add(tr)
            
            print(f"✅ {len(types_lpz)} types de relevés LPZ créés")
            
            # 6. Créer l'utilisateur admin
            print("\n6️⃣ CRÉATION DE L'UTILISATEUR ADMIN")
            print("-" * 40)
            
            admin = User()
            admin.username = 'admin'
            admin.password_hash = generate_password_hash('admin123')
            admin.role = 'admin'
            db.session.add(admin)
            
            print("✅ Utilisateur admin créé")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Role: admin")
            
            # 7. Créer les formulaires de routines
            print("\n7️⃣ CRÉATION DES FORMULAIRES DE ROUTINES")
            print("-" * 40)
            
            formulaires_routines = [
                'STE PRINCIPALE LPZ', 'STE CAB LPZ', 'STEP LPZ', 
                'STE PRINCIPALE SMP', 'STE CAB SMP', 'STEP SMP'
            ]
            
            for nom in formulaires_routines:
                formulaire = FormulaireRoutine()
                formulaire.nom = nom
                db.session.add(formulaire)
            
            print(f"✅ {len(formulaires_routines)} formulaires de routines créés")
            
            # 8. Créer la configuration email
            print("\n8️⃣ CRÉATION DE LA CONFIGURATION EMAIL")
            print("-" * 40)
            
            email_config = EmailConfig()
            email_config.email_address = 'admin@ste-releve.com'
            email_config.smtp_server = 'smtp.gmail.com'
            email_config.smtp_port = 587
            db.session.add(email_config)
            
            print("✅ Configuration email créée")
            
            # 9. Valider toutes les modifications
            print("\n9️⃣ VALIDATION DES MODIFICATIONS")
            print("-" * 40)
            
            db.session.commit()
            print("✅ Toutes les modifications validées")
            
            # 10. Vérification finale
            print("\n🔟 VÉRIFICATION FINALE")
            print("-" * 40)
            
            users_count = User.query.count()
            sites_count = Site.query.count()
            types_count = TypeReleve.query.count()
            formulaires_count = FormulaireRoutine.query.count()
            
            print(f"✅ {users_count} utilisateurs créés")
            print(f"✅ {sites_count} sites créés")
            print(f"✅ {types_count} types de relevés créés")
            print(f"✅ {formulaires_count} formulaires créés")
            
            print("\n" + "=" * 60)
            print("🎉 RÉINITIALISATION TERMINÉE AVEC SUCCÈS!")
            print("=" * 60)
            print("🔑 Vous pouvez maintenant vous connecter avec:")
            print("   Username: admin")
            print("   Password: admin123")
            
        except Exception as e:
            print(f"❌ ERREUR lors de la réinitialisation: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    reset_database() 