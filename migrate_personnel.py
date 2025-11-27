#!/usr/bin/env python3
"""
Script de migration pour ajouter la colonne is_manager et créer les tables de gestion du personnel
"""

import os
import sys
from sqlalchemy import text, inspect

# Ajouter le répertoire parent au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate_personnel():
    """Ajoute la colonne is_manager et crée les tables de gestion du personnel"""
    
    print("🔄 Début de la migration pour la gestion du personnel")
    
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            
            # 1. Ajouter la colonne is_manager à la table user
            print("\n📋 Étape 1: Vérification de la colonne is_manager...")
            try:
                columns = [col['name'] for col in inspector.get_columns('user')]
                
                if 'is_manager' not in columns:
                    print("   → Ajout de la colonne is_manager...")
                    with db.engine.connect() as conn:
                        # SQLite utilise INTEGER pour les booléens
                        if 'sqlite' in str(db.engine.url):
                            conn.execute(text('ALTER TABLE user ADD COLUMN is_manager INTEGER DEFAULT 0'))
                        else:
                            # PostgreSQL : user est un mot réservé, il faut utiliser des guillemets
                            conn.execute(text('ALTER TABLE "user" ADD COLUMN is_manager BOOLEAN DEFAULT FALSE'))
                        conn.commit()
                    print("   ✅ Colonne is_manager ajoutée avec succès")
                else:
                    print("   ✅ Colonne is_manager déjà présente")
            except Exception as e:
                print(f"   ❌ Erreur lors de l'ajout de la colonne is_manager: {e}")
                return False
            
            # 2. Créer les tables de gestion du personnel
            print("\n📋 Étape 2: Vérification des tables de gestion du personnel...")
            try:
                table_names = inspector.get_table_names()
                tables_to_create = ['personnel', 'working_days', 'leave_request', 'personnel_document', 'absence']
                tables_missing = [t for t in tables_to_create if t not in table_names]
                
                if tables_missing:
                    print(f"   → Création des tables manquantes: {', '.join(tables_missing)}...")
                    db.create_all()  # Cela va créer toutes les tables manquantes
                    print(f"   ✅ Tables créées avec succès: {', '.join(tables_missing)}")
                else:
                    print("   ✅ Toutes les tables de gestion du personnel sont déjà présentes")
            except Exception as e:
                print(f"   ❌ Erreur lors de la création des tables: {e}")
                return False
            
            print("\n✅ Migration terminée avec succès!")
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur générale lors de la migration: {e}")
            return False

if __name__ == '__main__':
    success = migrate_personnel()
    sys.exit(0 if success else 1)






