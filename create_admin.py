#!/usr/bin/env python3
"""
Script simple pour créer l'utilisateur admin
"""

import os
# URL PostgreSQL correcte
os.environ['DATABASE_URL'] = 'postgresql://ste_app_db_user:E0XNVVYAL8PoZ1Dzjz5PbpQNj0690GQ1adpg-d11s87p5pdvs73cckia0-a@d11s87p5pdvs73cckia0-a.oregon-postgres.render.com/ste_app_db'

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        print("🔧 Création de l'utilisateur admin...")
        
        # Vérifier si l'admin existe déjà
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("✅ Utilisateur admin existe déjà")
            return
        
        # Créer l'utilisateur admin
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        
        try:
            db.session.commit()
            print("✅ Utilisateur admin créé avec succès!")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Role: admin")
        except Exception as e:
            print(f"❌ Erreur lors de la création: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_admin() 