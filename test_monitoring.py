#!/usr/bin/env python3
"""
Script de test pour vérifier le monitoring de la base de données
"""

from app import app, db, User, Releve, PhotoReleve, ReponseRoutine

def test_monitoring():
    with app.app_context():
        print("=== TEST MONITORING BASE DE DONNÉES ===")
        
        # Vérifier la configuration
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"Configuration base de données: {db_uri[:50]}...")
        
        # Déterminer le type de base de données
        if 'postgresql' in db_uri or 'postgres' in db_uri:
            db_type = 'PostgreSQL'
            db_icon = 'database'
            db_color = 'primary'
        else:
            db_type = 'SQLite'
            db_icon = 'hdd'
            db_color = 'secondary'
        
        print(f"Type de base de données détecté: {db_type}")
        print(f"Icône: {db_icon}")
        print(f"Couleur: {db_color}")
        
        # Compter les enregistrements
        nb_releves = Releve.query.count()
        nb_photos = PhotoReleve.query.count()
        nb_routines = ReponseRoutine.query.count()
        nb_users = User.query.count()
        
        print(f"\nStatistiques:")
        print(f"  - Relevés: {nb_releves}")
        print(f"  - Photos: {nb_photos}")
        print(f"  - Routines: {nb_routines}")
        print(f"  - Utilisateurs: {nb_users}")
        
        # Estimation de la taille
        estimated_size_mb = (nb_releves * 0.001) + (nb_photos * 2) + (nb_routines * 0.001)
        usage_percent = round((estimated_size_mb / 1024) * 100, 1)
        
        print(f"\nTaille estimée: {estimated_size_mb:.2f} MB")
        print(f"Utilisation: {usage_percent}% de 1GB")
        
        # Statut de l'espace
        if estimated_size_mb > 900:
            status = 'critical'
            message = 'Base de données presque pleine ! Upgrade recommandé.'
        elif estimated_size_mb > 800:
            status = 'warning'
            message = 'Base de données proche de la limite.'
        else:
            status = 'ok'
            message = 'Espace suffisant.'
        
        print(f"\nStatut: {status}")
        print(f"Message: {message}")
        
        print("\n=== FIN TEST ===")

if __name__ == "__main__":
    test_monitoring() 