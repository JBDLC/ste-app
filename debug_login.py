#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'état de la base de données et des utilisateurs
à exécuter sur Render pour diagnostiquer les problèmes de connexion
"""

import os
import sys
from datetime import datetime

# Ajouter le répertoire courant au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User, Site, TypeReleve
    from werkzeug.security import generate_password_hash, check_password_hash
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def diagnostic_complet():
    """Diagnostic complet de la base de données"""
    print("🔍 DIAGNOSTIC COMPLET DE LA BASE DE DONNÉES")
    print("=" * 50)
    
    with app.app_context():
        try:
            # 1. Vérifier la connexion à la base
            print("\n1️⃣ VÉRIFICATION DE LA CONNEXION")
            print("-" * 30)
            
            # Tester la connexion
            db.engine.connect()
            print("✅ Connexion à la base de données réussie")
            
            # Vérifier le type de base utilisée
            db_url = app.config['SQLALCHEMY_DATABASE_URI']
            if 'postgresql' in db_url or 'postgres' in db_url:
                print(f"📊 Type de base: PostgreSQL")
                print(f"🔗 URL: {db_url[:50]}...")
            else:
                print(f"📊 Type de base: SQLite")
                print(f"🔗 URL: {db_url}")
            
        except Exception as e:
            print(f"❌ ERREUR: Impossible de se connecter à la base: {e}")
            return
        
        # 2. Vérifier les tables
        print("\n2️⃣ VÉRIFICATION DES TABLES")
        print("-" * 30)
        
        try:
            # Lister les tables existantes
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tables trouvées: {', '.join(tables)}")
            
            # Vérifier les tables essentielles
            tables_requises = ['user', 'site', 'type_releve']
            for table in tables_requises:
                if table in tables:
                    print(f"✅ Table '{table}' existe")
                else:
                    print(f"❌ Table '{table}' MANQUANTE")
                    
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des tables: {e}")
        
        # 3. Vérifier les utilisateurs
        print("\n3️⃣ VÉRIFICATION DES UTILISATEURS")
        print("-" * 30)
        
        try:
            users = User.query.all()
            print(f"👥 Nombre total d'utilisateurs: {len(users)}")
            
            if users:
                print("\n📋 Liste des utilisateurs:")
                for user in users:
                    print(f"   - ID: {user.id}, Username: '{user.username}', Role: '{user.role}'")
                    print(f"     Password hash: {user.password_hash[:20]}...")
                    
                    # Tester le mot de passe admin
                    if user.username == 'admin':
                        test_password = 'admin123'
                        if check_password_hash(user.password_hash, test_password):
                            print(f"     ✅ Mot de passe 'admin123' VALIDE pour admin")
                        else:
                            print(f"     ❌ Mot de passe 'admin123' INVALIDE pour admin")
                            
                            # Créer un nouveau hash pour admin123
                            new_hash = generate_password_hash('admin123')
                            print(f"     🔧 Nouveau hash pour 'admin123': {new_hash[:20]}...")
                            
                            # Mettre à jour le mot de passe
                            user.password_hash = new_hash
                            db.session.commit()
                            print(f"     ✅ Mot de passe admin mis à jour!")
            else:
                print("❌ AUCUN UTILISATEUR TROUVÉ!")
                print("🔧 Création de l'utilisateur admin...")
                
                admin = User()
                admin.username = 'admin'
                admin.password_hash = generate_password_hash('admin123')
                admin.role = 'admin'
                db.session.add(admin)
                db.session.commit()
                print("✅ Utilisateur admin créé avec succès!")
                print("   Username: admin")
                print("   Password: admin123")
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des utilisateurs: {e}")
        
        # 4. Vérifier les sites
        print("\n4️⃣ VÉRIFICATION DES SITES")
        print("-" * 30)
        
        try:
            sites = Site.query.all()
            print(f"🏭 Nombre de sites: {len(sites)}")
            
            if sites:
                for site in sites:
                    print(f"   - ID: {site.id}, Nom: '{site.nom}', Description: '{site.description}'")
            else:
                print("❌ AUCUN SITE TROUVÉ!")
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des sites: {e}")
        
        # 5. Vérifier les types de relevés
        print("\n5️⃣ VÉRIFICATION DES TYPES DE RELEVÉS")
        print("-" * 30)
        
        try:
            types = TypeReleve.query.all()
            print(f"📊 Nombre de types de relevés: {len(types)}")
            
            if types:
                sites_count = {}
                for tr in types:
                    site_nom = "SMP" if tr.site_id == 1 else "LPZ" if tr.site_id == 2 else f"Site {tr.site_id}"
                    sites_count[site_nom] = sites_count.get(site_nom, 0) + 1
                
                for site, count in sites_count.items():
                    print(f"   - {site}: {count} types de relevés")
            else:
                print("❌ AUCUN TYPE DE RELEVÉ TROUVÉ!")
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des types de relevés: {e}")
        
        # 6. Test de connexion admin
        print("\n6️⃣ TEST DE CONNEXION ADMIN")
        print("-" * 30)
        
        try:
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                test_password = 'admin123'
                if check_password_hash(admin_user.password_hash, test_password):
                    print("✅ Test de connexion admin RÉUSSI")
                    print("   Username: admin")
                    print("   Password: admin123")
                    print("   Role: admin")
                else:
                    print("❌ Test de connexion admin ÉCHOUÉ")
                    print("   Le mot de passe 'admin123' ne correspond pas au hash stocké")
            else:
                print("❌ Utilisateur admin non trouvé!")
                
        except Exception as e:
            print(f"❌ Erreur lors du test de connexion: {e}")
        
        print("\n" + "=" * 50)
        print("🏁 DIAGNOSTIC TERMINÉ")

if __name__ == '__main__':
    diagnostic_complet() 