#!/usr/bin/env python3
"""
Script simple pour créer les types de relevés dans PostgreSQL
"""

import os
import sys

# Ajouter le répertoire courant au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, Site, TypeReleve
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)

def create_types_releve():
    """Créer les types de relevés"""
    print("🔧 CRÉATION DES TYPES DE RELEVÉS")
    print("=" * 40)
    
    with app.app_context():
        try:
            # 1. Créer les sites s'ils n'existent pas
            print("\n1️⃣ VÉRIFICATION DES SITES")
            print("-" * 30)
            
            smp = Site.query.filter_by(nom='SMP').first()
            if not smp:
                smp = Site(nom='SMP', description='Station de traitement des eaux SMP')
                db.session.add(smp)
                db.session.commit()
                print("✅ Site SMP créé")
            else:
                print("✅ Site SMP existe déjà")
            
            lpz = Site.query.filter_by(nom='LPZ').first()
            if not lpz:
                lpz = Site(nom='LPZ', description='Station de traitement des eaux LPZ')
                db.session.add(lpz)
                db.session.commit()
                print("✅ Site LPZ créé")
            else:
                print("✅ Site LPZ existe déjà")
            
            # 2. Créer les types de relevés pour SMP
            print("\n2️⃣ CRÉATION DES TYPES DE RELEVÉS SMP")
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
            
            count_smp = 0
            for nom, type_mesure, unite, frequence, *args in types_smp:
                jour_specifique = args[0] if args else None
                
                # Vérifier si le type existe déjà
                existing = TypeReleve.query.filter_by(nom=nom, site_id=smp.id).first()
                if not existing:
                    tr = TypeReleve()
                    tr.nom = nom
                    tr.site_id = smp.id
                    tr.type_mesure = type_mesure
                    tr.unite = unite
                    tr.frequence = frequence
                    tr.jour_specifique = jour_specifique
                    db.session.add(tr)
                    count_smp += 1
                    print(f"   ✅ {nom}")
            
            # 3. Créer les types de relevés pour LPZ
            print("\n3️⃣ CRÉATION DES TYPES DE RELEVÉS LPZ")
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
            
            count_lpz = 0
            for nom, type_mesure, unite, frequence, *args in types_lpz:
                jour_specifique = args[0] if args else None
                
                # Vérifier si le type existe déjà
                existing = TypeReleve.query.filter_by(nom=nom, site_id=lpz.id).first()
                if not existing:
                    tr = TypeReleve()
                    tr.nom = nom
                    tr.site_id = lpz.id
                    tr.type_mesure = type_mesure
                    tr.unite = unite
                    tr.frequence = frequence
                    tr.jour_specifique = jour_specifique
                    db.session.add(tr)
                    count_lpz += 1
                    print(f"   ✅ {nom}")
            
            # 4. Valider les modifications
            print("\n4️⃣ VALIDATION")
            print("-" * 30)
            
            db.session.commit()
            print(f"✅ {count_smp} types SMP créés")
            print(f"✅ {count_lpz} types LPZ créés")
            
            # 5. Vérification finale
            print("\n5️⃣ VÉRIFICATION FINALE")
            print("-" * 30)
            
            total_smp = TypeReleve.query.filter_by(site_id=smp.id).count()
            total_lpz = TypeReleve.query.filter_by(site_id=lpz.id).count()
            
            print(f"📊 Total types SMP: {total_smp}")
            print(f"📊 Total types LPZ: {total_lpz}")
            
            print("\n" + "=" * 40)
            print("🎉 TYPES DE RELEVÉS CRÉÉS AVEC SUCCÈS!")
            print("=" * 40)
            print("🔗 Vous pouvez maintenant voir le tableau dans l'application")
            
        except Exception as e:
            print(f"❌ ERREUR: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    create_types_releve() 