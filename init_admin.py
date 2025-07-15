#!/usr/bin/env python3
"""
Script pour initialiser l'utilisateur admin dans la base PostgreSQL
"""

from app import app, db, User, Site, TypeReleve
from werkzeug.security import generate_password_hash
from datetime import datetime

def init_admin():
    with app.app_context():
        print("🔧 Initialisation de l'utilisateur admin...")
        
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
        
        # Créer les sites s'ils n'existent pas
        if not Site.query.first():
            print("🏭 Création des sites...")
            smp = Site(nom='SMP', description='Station de traitement des eaux SMP')
            lpz = Site(nom='LPZ', description='Station de traitement des eaux LPZ')
            db.session.add(smp)
            db.session.add(lpz)
        
        # Créer les types de relevés s'ils n'existent pas
        if not TypeReleve.query.first():
            print("📊 Création des types de relevés...")
            # Types SMP
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
                tr = TypeReleve(
                    nom=nom,
                    site_id=1,  # SMP
                    type_mesure=type_mesure,
                    unite=unite,
                    frequence=frequence,
                    jour_specifique=jour_specifique
                )
                db.session.add(tr)
            
            # Types LPZ
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
                tr = TypeReleve(
                    nom=nom,
                    site_id=2,  # LPZ
                    type_mesure=type_mesure,
                    unite=unite,
                    frequence=frequence,
                    jour_specifique=jour_specifique
                )
                db.session.add(tr)
        
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
    init_admin() 