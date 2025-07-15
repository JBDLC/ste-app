#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier la configuration Render et PostgreSQL
"""

import os
import sys

def diagnostic_render():
    print("🔍 DIAGNOSTIC RENDER ET POSTGRESQL")
    print("=" * 50)
    
    # 1. Vérifier les variables d'environnement
    print("\n1. Variables d'environnement:")
    print(f"   RENDER: {os.environ.get('RENDER', 'Non défini')}")
    print(f"   DATABASE_URL: {os.environ.get('DATABASE_URL', 'Non défini')[:50] if os.environ.get('DATABASE_URL') else 'Non défini'}")
    
    # 2. Vérifier la configuration de l'app
    print("\n2. Configuration de l'application:")
    try:
        from app import app
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"   SQLALCHEMY_DATABASE_URI: {db_uri[:50]}...")
        
        if 'postgresql' in db_uri or 'postgres' in db_uri:
            print("   ✅ Type: PostgreSQL")
        else:
            print("   ❌ Type: SQLite (PROBLÈME!)")
            
    except Exception as e:
        print(f"   ❌ Erreur lors de l'import: {e}")
    
    # 3. Tester la connexion à la base
    print("\n3. Test de connexion à la base:")
    try:
        from app import app, db
        with app.app_context():
            db.engine.connect()
            print("   ✅ Connexion réussie!")
            
            # Compter les tables
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   📋 Tables trouvées: {len(tables)}")
            for table in tables:
                print(f"      - {table}")
                
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
    
    # 4. Vérifier les données existantes
    print("\n4. Données existantes:")
    try:
        from app import app, db, User, Releve, Site
        with app.app_context():
            nb_users = User.query.count()
            nb_releves = Releve.query.count()
            nb_sites = Site.query.count()
            
            print(f"   👥 Utilisateurs: {nb_users}")
            print(f"   📊 Relevés: {nb_releves}")
            print(f"   🏭 Sites: {nb_sites}")
            
            if nb_users == 0:
                print("   ⚠️ Aucun utilisateur trouvé - base vide ou problème d'initialisation")
            if nb_releves == 0:
                print("   ⚠️ Aucun relevé trouvé - données perdues ou problème d'initialisation")
                
    except Exception as e:
        print(f"   ❌ Erreur lors du comptage: {e}")
    
    # 5. Vérifier le render.yaml
    print("\n5. Configuration render.yaml:")
    try:
        with open('render.yaml', 'r') as f:
            content = f.read()
            if 'ste-app-db' in content:
                print("   ✅ Base 'ste-app-db' référencée dans render.yaml")
            else:
                print("   ❌ Base 'ste-app-db' NON trouvée dans render.yaml")
                
            if 'DATABASE_URL' in content:
                print("   ✅ DATABASE_URL configuré dans render.yaml")
            else:
                print("   ❌ DATABASE_URL NON configuré dans render.yaml")
                
    except Exception as e:
        print(f"   ❌ Erreur lecture render.yaml: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 DIAGNOSTIC TERMINÉ")

if __name__ == '__main__':
    diagnostic_render() 