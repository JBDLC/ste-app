from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import plotly.graph_objs as go
import plotly.utils
import json
from werkzeug.utils import secure_filename
from sqlalchemy import func, text, case
from typing import Union, Tuple
from fpdf import FPDF
import matplotlib.pyplot as plt
import io
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre_cle_secrete_ici'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ste_releve.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Modèles de base de données
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='operateur')  # operateur, chef_equipe, admin

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)  # SMP ou LPZ
    description = db.Column(db.String(200))

class TypeReleve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    type_mesure = db.Column(db.String(20), nullable=False)  # totalisateur, basique, hebdomadaire
    unite = db.Column(db.String(20), nullable=False)
    frequence = db.Column(db.String(20), default='quotidien')  # quotidien, hebdomadaire
    jour_specifique = db.Column(db.String(20))  # lundi pour eau potable et coagulant

class Releve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    type_releve_id = db.Column(db.Integer, db.ForeignKey('type_releve.id'), nullable=False)
    valeur = db.Column(db.Float, nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    commentaire = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PhotoReleve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('site.id'), nullable=False)
    nom_debitmetre = db.Column(db.String(100), nullable=False)
    fichier_photo = db.Column(db.String(200), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    commentaire = db.Column(db.Text)
    session_id = db.Column(db.String(50), nullable=False)  # Identifiant unique de la session de relevé
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Modèles pour les routines d'exploitation
class FormulaireRoutine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class QuestionRoutine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    formulaire_id = db.Column(db.Integer, db.ForeignKey('formulaire_routine.id'), nullable=False)
    id_question = db.Column(db.String(50), nullable=False)
    lieu = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    ordre = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReponseRoutine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    formulaire_id = db.Column(db.Integer, db.ForeignKey('formulaire_routine.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question_routine.id'), nullable=False)
    reponse = db.Column(db.String(20), nullable=False)  # 'Fait', 'Non Fait', 'Non Applicable'
    commentaire = db.Column(db.Text)
    photo_path = db.Column(db.String(200))
    date_creation = db.Column(db.Date, default=datetime.utcnow().date)
    heure_creation = db.Column(db.Time, default=datetime.utcnow().time)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes principales
@app.route('/')
@login_required
def index():
    sites = Site.query.all()
    return render_template('index.html', sites=sites)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/releve/<int:site_id>')
@login_required
def releve_site(site_id):
    if site_id == 1:
        return render_template('releve_smp.html')
    elif site_id == 2:
        return render_template('releve_lpz.html')
    else:
        return "Site inconnu", 404

@app.route('/api/releve', methods=['POST'])
@login_required
def ajouter_releve():
    data = request.get_json()
    print(f"DEBUG /api/releve - Données reçues: {data}")
    
    # Utiliser la date fournie ou aujourd'hui
    if 'date' in data and data['date']:
        date_releve = datetime.strptime(data['date'], '%Y-%m-%d').date()
    else:
        date_releve = datetime.now().date()
    
    if 'id' in data and data['id']:
        # Modification d'un relevé existant
        print(f"DEBUG /api/releve - Modification du relevé ID: {data['id']}")
        releve = Releve.query.get(data['id'])
        if releve:
            print(f"DEBUG /api/releve - Relevé trouvé: date={releve.date}, valeur={releve.valeur}, type_id={releve.type_releve_id}")
            
            # Utiliser le type_releve_id fourni ou garder l'ancien si undefined
            type_releve_id = data.get('type_releve_id')
            if type_releve_id == 'undefined' or not type_releve_id:
                type_releve_id = releve.type_releve_id
                print(f"DEBUG /api/releve - Type_releve_id undefined, utilisation de l'ancien: {type_releve_id}")
            
            print(f"DEBUG /api/releve - Nouvelles valeurs: date={date_releve}, valeur={data['valeur']}, type_id={type_releve_id}")
            
            releve.valeur = data['valeur']
            releve.commentaire = data.get('commentaire', '')
            releve.date = date_releve
            releve.type_releve_id = type_releve_id
            releve.utilisateur_id = current_user.id
            db.session.commit()
            print(f"DEBUG /api/releve - Relevé mis à jour avec succès")
            return jsonify({'success': True})
        else:
            print(f"DEBUG /api/releve - Relevé non trouvé pour ID: {data['id']}")
            return jsonify({'success': False, 'message': 'Relevé non trouvé'}), 404
    # Sinon, comportement existant (création ou update par date/type)
    releve_existant = Releve.query.filter_by(
        type_releve_id=data['type_releve_id'],
        date=date_releve
    ).first()
    if releve_existant:
        releve_existant.valeur = data['valeur']
        releve_existant.commentaire = data.get('commentaire', '')
        releve_existant.utilisateur_id = current_user.id
    else:
        nouveau_releve = Releve(
            date=date_releve,
            type_releve_id=data['type_releve_id'],
            valeur=data['valeur'],
            commentaire=data.get('commentaire', ''),
            utilisateur_id=current_user.id
        )
        db.session.add(nouveau_releve)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/historique')
@login_required
def historique():
    sites = Site.query.all()
    return render_template('historique.html', sites=sites)

@app.route('/api/historique/<int:site_id>')
@login_required
def get_historique(site_id):
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    
    query = db.session.query(Releve, TypeReleve).join(TypeReleve).filter(TypeReleve.site_id == site_id)
    
    if date_debut:
        query = query.filter(Releve.date >= datetime.strptime(date_debut, '%Y-%m-%d').date())
    if date_fin:
        query = query.filter(Releve.date <= datetime.strptime(date_fin, '%Y-%m-%d').date())
    
    # Tri : date décroissante, puis id de TypeReleve croissant (ordre métier)
    releves = query.order_by(Releve.date.desc(), TypeReleve.id.asc()).all()
    
    result = []
    for releve, type_releve in releves:
        user = db.session.get(User, releve.utilisateur_id)
        result.append({
            'id': releve.id,
            'date': releve.date.strftime('%Y-%m-%d'),
            'type_releve': type_releve.nom,
            'valeur': releve.valeur,
            'unite': type_releve.unite,
            'commentaire': releve.commentaire,
            'utilisateur': user.username if user else 'Inconnu'
        })
    
    return jsonify(result)

@app.route('/export_excel/<int:site_id>')
@login_required
def export_excel(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        return "Site non trouvé", 404
    
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    
    # Récupérer tous les types de relevé (débitmètres) pour ce site, triés par id
    types_releve = TypeReleve.query.filter_by(site_id=site_id).order_by(TypeReleve.id).all()
    noms_debitmetres = [tr.nom for tr in types_releve]
    id_debitmetres = {tr.id: tr.nom for tr in types_releve}
    unites = {tr.nom: tr.unite for tr in types_releve}
    
    # Récupérer tous les relevés de la période
    query = db.session.query(Releve).filter(Releve.type_releve_id.in_(id_debitmetres.keys()))
    if date_debut:
        query = query.filter(Releve.date >= datetime.strptime(date_debut, '%Y-%m-%d').date())
    if date_fin:
        query = query.filter(Releve.date <= datetime.strptime(date_fin, '%Y-%m-%d').date())
    releves = query.all()
    
    # Construire le pivot : {date: {nom_debitmetre: valeur}}
    donnees = {}
    for r in releves:
        d = r.date.strftime('%Y-%m-%d')
        nom = id_debitmetres[r.type_releve_id]
        if d not in donnees:
            donnees[d] = {}
        donnees[d][nom] = r.valeur
    
    # Toutes les dates de la période (même sans relevé)
    if date_debut and date_fin:
        d1 = datetime.strptime(date_debut, '%Y-%m-%d').date()
        d2 = datetime.strptime(date_fin, '%Y-%m-%d').date()
        toutes_les_dates = [(d1 + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((d2-d1).days+1)]
    else:
        toutes_les_dates = sorted(donnees.keys())
    
    # Créer le fichier Excel
    wb = Workbook()
    ws = wb.active
    if ws:
        ws.title = f"Relevés {site.nom}"
        
        # En-têtes : Date + noms de débitmètres
        ws.cell(row=1, column=1, value='Date').font = Font(bold=True)
        for i, nom in enumerate(noms_debitmetres, 2):
            cell = ws.cell(row=1, column=i, value=nom)
            cell.font = Font(bold=True)
        
        # Données
        for row, date in enumerate(toutes_les_dates, 2):
            ws.cell(row=row, column=1, value=date)
            for col, nom in enumerate(noms_debitmetres, 2):
                valeur = donnees.get(date, {}).get(nom, '')
                ws.cell(row=row, column=col, value=valeur)
    
    # Sauvegarder le fichier
    filename = f"releves_{site.nom}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    wb.save(filepath)
    
    print('DEBUG EXPORT EXCEL - Colonnes générées:', noms_debitmetres)
    
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/indicateurs')
@login_required
def indicateurs():
    sites = Site.query.all()
    return render_template('indicateurs.html', sites=sites)

@app.route('/api/indicateurs/<int:site_id>')
@login_required
def get_indicateurs(site_id):
    site = Site.query.get_or_404(site_id)
    jours = request.args.get('jours', 30, type=int)
    date_debut = datetime.now().date() - timedelta(days=jours)
    
    # Récupérer tous les types de relevés du site
    types_releve = TypeReleve.query.filter_by(site_id=site_id).all()
    
    result = []
    for type_releve in types_releve:
        if type_releve.type_mesure == 'totalisateur':
            # Calculer les débits journaliers pour les totalisateurs
            releves = Releve.query.filter_by(type_releve_id=type_releve.id).filter(
                Releve.date >= date_debut
            ).order_by(Releve.date).all()
            
            if len(releves) > 1:
                valeurs = []
                for i in range(1, len(releves)):
                    difference = releves[i].valeur - releves[i-1].valeur
                    valeurs.append({
                        'date': releves[i].date.strftime('%Y-%m-%d'),
                        'valeur': difference
                    })
                
                result.append({
                    'nom': type_releve.nom,
                    'unite': type_releve.unite,
                    'valeurs': valeurs
                })
        else:
            # Relevés basiques
            releves = Releve.query.filter_by(type_releve_id=type_releve.id).filter(
                Releve.date >= date_debut
            ).order_by(Releve.date).all()
            
            if releves:
                valeurs = [{
                    'date': r.date.strftime('%Y-%m-%d'),
                    'valeur': r.valeur
                } for r in releves]
                
                result.append({
                    'nom': type_releve.nom,
                    'unite': type_releve.unite,
                    'valeurs': valeurs
                })
    
    return jsonify(result)

@app.route('/releve_20')
@login_required
def releve_20():
    sites = Site.query.all()
    return render_template('releve_20.html', sites=sites)

@app.route('/api/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
    
    site_nom = request.form.get('site_id')  # Renommé pour clarifier
    nom_debitmetre = request.form.get('nom_debitmetre')
    commentaire = request.form.get('commentaire', '')
    
    if not all([site_nom, nom_debitmetre]):
        return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
    
    try:
        # Convertir le nom du site en ID
        site = Site.query.filter_by(nom=site_nom).first()
        if not site:
            return jsonify({'success': False, 'message': f'Site {site_nom} non trouvé'}), 400
        
        site_id = site.id  # ID numérique du site
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{secure_filename(file.filename or 'photo.jpg')}"
        
        # Utiliser le session_id envoyé par le frontend ou en générer un par défaut
        session_id = request.form.get('session_id')
        if not session_id:
            session_id = f"{current_user.id}_{site_nom}_{timestamp}"
        
        # Sauvegarder le fichier
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Enregistrer en base de données
        photo = PhotoReleve(
            date=datetime.now().date(),
            site_id=site_id,  # Utiliser l'ID numérique
            nom_debitmetre=nom_debitmetre,
            fichier_photo=filename,
            utilisateur_id=current_user.id,
            commentaire=commentaire,
            session_id=session_id
        )
        
        db.session.add(photo)
        db.session.commit()
        
        # Log pour debug
        print(f"PHOTO ENREGISTREE: {{'site_id': {site_id}, 'site_nom': '{site_nom}', 'nom_debitmetre': '{nom_debitmetre}', 'utilisateur_id': {current_user.id}, 'date': {photo.date}, 'fichier_photo': '{filename}', 'session_id': '{session_id}'}}")
        
        return jsonify({'success': True, 'message': 'Photo enregistrée avec succès'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur lors de l\'enregistrement: {str(e)}'}), 500

@app.route('/api/releve_20_status')
@login_required
def get_releve_20_status():
    """Récupère le statut des relevés du 20 pour chaque site"""
    try:
        # Débitmètres à photographier par site
        debitmetres_smp = [
            'Exhaure 1', 'Exhaure 2', 'Exhaure 3', 'Exhaure 4', 
            'Retour dessableur', 'Retour Orage'
        ]
        debitmetres_lpz = [
            'Exhaure 1', 'Exhaure 2', 'Retour dessableur'
        ]
        
        # Récupérer les sites
        site_smp = Site.query.filter_by(nom='SMP').first()
        site_lpz = Site.query.filter_by(nom='LPZ').first()
        
        # Fonction pour vérifier le statut d'un débitmètre
        def get_debitmetre_status(site_id, nom_debitmetre):
            # Vérifier s'il y a une photo pour ce débitmètre aujourd'hui
            photo_aujourd_hui = PhotoReleve.query.filter_by(
                site_id=site_id,
                nom_debitmetre=nom_debitmetre,
                date=datetime.now().date()
            ).first()
            
            if photo_aujourd_hui:
                return 'Terminé'
            else:
                # Vérifier s'il y a des photos récentes (ce mois)
                debut_mois = datetime.now().replace(day=1).date()
                photo_ce_mois = PhotoReleve.query.filter_by(
                    site_id=site_id,
                    nom_debitmetre=nom_debitmetre
                ).filter(PhotoReleve.date >= debut_mois).first()
                
                if photo_ce_mois:
                    return 'En cours'
                else:
                    return 'En attente'
        
        # Statut SMP
        smp_status = []
        if site_smp:
            for debitmetre in debitmetres_smp:
                smp_status.append({
                    'nom': debitmetre,
                    'statut': get_debitmetre_status(site_smp.id, debitmetre)
                })
        
        # Statut LPZ
        lpz_status = []
        if site_lpz:
            for debitmetre in debitmetres_lpz:
                lpz_status.append({
                    'nom': debitmetre,
                    'statut': get_debitmetre_status(site_lpz.id, debitmetre)
                })
        
        return jsonify({
            'success': True,
            'smp': smp_status,
            'lpz': lpz_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/photos')
@login_required
def photos():
    photos = PhotoReleve.query.order_by(PhotoReleve.date.desc()).all()
    return render_template('photos.html', photos=photos)

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/api/liste_releves_20')
@login_required
def liste_releves_20():
    print("=== DIAGNOSTIC liste_releves_20 ===")
    
    # Récupérer toutes les photos, groupées par session_id (pas seulement aujourd'hui)
    photos = PhotoReleve.query.order_by(PhotoReleve.date.desc()).all()
    
    # Grouper par session_id
    sessions = {}
    for photo in photos:
        if photo.session_id not in sessions:
            sessions[photo.session_id] = {
                'date': photo.date,
                'site_id': photo.site_id,
                'utilisateur_id': photo.utilisateur_id,
                'photos': []
            }
        sessions[photo.session_id]['photos'].append(photo)
    
    print(f"Résultat du groupement par session: {[(session_id, data['date'], data['site_id'], data['utilisateur_id'], len(data['photos'])) for session_id, data in sessions.items()]}")
    
    result = []
    for session_id, data in sessions.items():
        print(f"Traitement session: {session_id}, date={data['date']}, site_id={data['site_id']}, utilisateur_id={data['utilisateur_id']}, nb_photos={len(data['photos'])}")
        
        # Récupérer les informations du site et de l'utilisateur
        # Gérer les deux formats : site_id comme entier ou comme chaîne
        site = None
        if isinstance(data['site_id'], int):
            # Nouveau format : site_id est un entier
            site = db.session.get(Site, data['site_id'])
        else:
            # Ancien format : site_id est une chaîne (nom du site)
            site = Site.query.filter_by(nom=data['site_id']).first()
        
        user = db.session.get(User, data['utilisateur_id'])
        
        if site and user:
            result.append({
                'session_id': session_id,
                'date': data['date'].strftime('%d/%m/%Y'),
                'date_iso': data['date'].strftime('%Y-%m-%d'),
                'site': site.nom,
                'site_id': data['site_id'],
                'utilisateur': user.username,
                'utilisateur_id': data['utilisateur_id'],
                'nb_photos': len(data['photos'])
            })
    
    print(f"Relevés finaux: {result}")
    print("=== FIN DIAGNOSTIC ===")
    return jsonify(result)

@app.route('/api/photos_releve_20')
@login_required
def photos_releve_20():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Paramètre session_id manquant'}), 400
    
    photos = PhotoReleve.query.filter_by(session_id=session_id).all()
    result = []
    for p in photos:
        user = User.query.get(p.utilisateur_id)
        result.append({
            'nom_debitmetre': p.nom_debitmetre,
            'fichier_photo': p.fichier_photo,
            'commentaire': p.commentaire,
            'date': p.date.strftime('%d/%m/%Y'),
            'utilisateur': user.username if user else p.utilisateur_id
        })
    return jsonify(result)

@app.route('/api/supprimer_releve_20', methods=['DELETE'])
@login_required
def supprimer_releve_20():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'message': 'Paramètre session_id manquant'}), 400
    
    try:
        # Récupérer toutes les photos de cette session
        photos = PhotoReleve.query.filter_by(session_id=session_id).all()
        
        # Supprimer les fichiers physiques
        for photo in photos:
            try:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo.fichier_photo)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Erreur lors de la suppression du fichier {photo.fichier_photo}: {e}")
        
        # Supprimer les enregistrements de la base
        PhotoReleve.query.filter_by(session_id=session_id).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Relevé supprimé avec succès ({len(photos)} photos)'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'}), 500

@app.route('/api/veille_releve_20/<site_id>')
@login_required
def veille_releve_20(site_id):
    # Récupérer la date d'hier
    hier = datetime.now().date() - timedelta(days=1)
    # Récupérer tous les types de relevé pour ce site
    types = TypeReleve.query.filter_by(site_id=Site.query.filter_by(nom=site_id).first().id).all()
    result = {}
    for tr in types:
        # On ne prend que les débitmètres (totalisateur)
        if tr.type_mesure == 'totalisateur':
            releve_hier = Releve.query.filter_by(type_releve_id=tr.id, date=hier).first()
            result[tr.nom] = releve_hier.valeur if releve_hier else None
    return jsonify(result)

@app.route('/api/releves_jour/<int:site_id>')
@login_required
def api_releves_jour(site_id):
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date manquante'}), 400
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'Format de date invalide'}), 400
    types_releve = TypeReleve.query.filter_by(site_id=site_id).all()
    result = {}
    for tr in types_releve:
        releve = Releve.query.filter_by(type_releve_id=tr.id, date=date_obj).first()
        if releve:
            result[tr.id] = {
                'valeur': releve.valeur,
                'unite': tr.unite
            }
    return jsonify(result)

# Nouvelles routes API pour les relevés SMP et LPZ
@app.route('/api/releves_smp', methods=['GET', 'POST'])
@login_required
def api_releves_smp() -> Union[Response, Tuple[Response, int]]:
    if request.method == 'GET':
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date requise'}), 400
        
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Format de date invalide'}), 400
        
        # Récupérer tous les types de relevé pour SMP
        types_releve = TypeReleve.query.filter_by(site_id=1).order_by(TypeReleve.id).all()
        
        # Récupérer les relevés existants pour cette date
        releves_existants = Releve.query.join(TypeReleve).filter(
            TypeReleve.site_id == 1,
            Releve.date == date_obj
        ).all()
        
        # Créer un dictionnaire des relevés existants
        releves_dict = {r.type_releve_id: r for r in releves_existants}
        
        result = []
        for tr in types_releve:
            releve = releves_dict.get(tr.id)
            result.append({
                'id': tr.id,
                'nom': tr.nom,
                'type_mesure': tr.type_mesure,
                'unite': tr.unite,
                'frequence': tr.frequence,
                'jour_specifique': tr.jour_specifique,
                'valeur': releve.valeur if releve else None,
                'commentaire': releve.commentaire if releve else '',
                'releve_id': releve.id if releve else None
            })
        
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        try:
            date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            return jsonify({'error': 'Date invalide'}), 400
        
        # Traiter chaque relevé
        for releve_data in data.get('releves', []):
            type_releve_id = releve_data.get('type_releve_id')
            valeur = releve_data.get('valeur')
            
            if type_releve_id is None or valeur is None:
                continue
            
            # Vérifier si un relevé existe déjà
            releve_existant = Releve.query.filter_by(
                type_releve_id=type_releve_id,
                date=date_obj
            ).first()
            
            if releve_existant:
                # Mettre à jour le relevé existant
                releve_existant.valeur = valeur
                releve_existant.commentaire = releve_data.get('commentaire', '')
                releve_existant.utilisateur_id = current_user.id
            else:
                # Créer un nouveau relevé
                nouveau_releve = Releve(
                    date=date_obj,
                    type_releve_id=type_releve_id,
                    valeur=valeur,
                    commentaire=releve_data.get('commentaire', ''),
                    utilisateur_id=current_user.id
                )
                db.session.add(nouveau_releve)
        
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erreur lors de la sauvegarde: {str(e)}'}), 500
    
    # Valeur de retour par défaut pour les méthodes non supportées
    return jsonify({'error': 'Méthode non supportée'}), 405

@app.route('/api/releves_lpz', methods=['GET', 'POST'])
@login_required
def api_releves_lpz() -> Union[Response, Tuple[Response, int]]:
    if request.method == 'GET':
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date requise'}), 400
        
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Format de date invalide'}), 400
        
        # Récupérer tous les types de relevé pour LPZ
        types_releve = TypeReleve.query.filter_by(site_id=2).order_by(TypeReleve.id).all()
        
        # Récupérer les relevés existants pour cette date
        releves_existants = Releve.query.join(TypeReleve).filter(
            TypeReleve.site_id == 2,
            Releve.date == date_obj
        ).all()
        
        # Créer un dictionnaire des relevés existants
        releves_dict = {r.type_releve_id: r for r in releves_existants}
        
        result = []
        for tr in types_releve:
            releve = releves_dict.get(tr.id)
            result.append({
                'id': tr.id,
                'nom': tr.nom,
                'type_mesure': tr.type_mesure,
                'unite': tr.unite,
                'frequence': tr.frequence,
                'jour_specifique': tr.jour_specifique,
                'valeur': releve.valeur if releve else None,
                'commentaire': releve.commentaire if releve else '',
                'releve_id': releve.id if releve else None
            })
        
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        try:
            date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            return jsonify({'error': 'Date invalide'}), 400
        
        # Traiter chaque relevé
        for releve_data in data.get('releves', []):
            type_releve_id = releve_data.get('type_releve_id')
            valeur = releve_data.get('valeur')
            
            if type_releve_id is None or valeur is None:
                continue
            
            # Vérifier si un relevé existe déjà
            releve_existant = Releve.query.filter_by(
                type_releve_id=type_releve_id,
                date=date_obj
            ).first()
            
            if releve_existant:
                # Mettre à jour le relevé existant
                releve_existant.valeur = valeur
                releve_existant.commentaire = releve_data.get('commentaire', '')
                releve_existant.utilisateur_id = current_user.id
            else:
                # Créer un nouveau relevé
                nouveau_releve = Releve(
                    date=date_obj,
                    type_releve_id=type_releve_id,
                    valeur=valeur,
                    commentaire=releve_data.get('commentaire', ''),
                    utilisateur_id=current_user.id
                )
                db.session.add(nouveau_releve)
        
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Erreur lors de la sauvegarde: {str(e)}'}), 500
    
    # Valeur de retour par défaut pour les méthodes non supportées
    return jsonify({'error': 'Méthode non supportée'}), 405

@app.route('/api/veille/<int:site_id>')
@login_required
def api_veille(site_id):
    # Récupérer les valeurs de la veille pour un site donné
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date requise'}), 400
    
    date_releve = datetime.strptime(date_str, '%Y-%m-%d').date()
    date_veille = date_releve - timedelta(days=1)
    
    # Récupérer tous les types de relevé pour ce site
    types_releve = TypeReleve.query.filter_by(site_id=site_id).all()
    
    # Récupérer les relevés de la veille
    releves_veille = {}
    for tr in types_releve:
        releve = Releve.query.filter_by(
            type_releve_id=tr.id,
            date=date_veille
        ).first()
        if releve:
            releves_veille[tr.nom] = releve.valeur
    
    return jsonify({
        'date_veille': date_veille.strftime('%Y-%m-%d'),
        'releves': releves_veille
    })

@app.route('/api/verifier_existence/<int:site_id>')
@login_required
def api_verifier_existence(site_id):
    # Vérifier si des relevés existent déjà pour une date donnée
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date requise'}), 400
    
    date_releve = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Récupérer tous les types de relevé pour ce site
    types_releve = TypeReleve.query.filter_by(site_id=site_id).all()
    
    # Vérifier les relevés existants
    releves_existants = []
    for tr in types_releve:
        releve = Releve.query.filter_by(
            type_releve_id=tr.id,
            date=date_releve
        ).first()
        if releve:
            releves_existants.append({
                'nom': tr.nom,
                'valeur': releve.valeur,
                'utilisateur': User.query.get(releve.utilisateur_id).username
            })
    
    return jsonify({
        'date': date_str,
        'existe': len(releves_existants) > 0,
        'releves_existants': releves_existants
    })

@app.route('/api/releve/<int:releve_id>', methods=['DELETE'])
@login_required
def supprimer_releve(releve_id):
    try:
        releve = Releve.query.get_or_404(releve_id)
        db.session.delete(releve)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Relevé supprimé avec succès'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression: {str(e)}'}), 500

@app.route('/api/releves_jour/<int:site_id>', methods=['DELETE'])
@login_required
def supprimer_releves_jour(site_id):
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'success': False, 'message': 'Date requise'}), 400
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        types_releve = TypeReleve.query.filter_by(site_id=site_id).all()
        type_ids = [tr.id for tr in types_releve]
        Releve.query.filter(Releve.type_releve_id.in_(type_ids), Releve.date == date_obj).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Tous les relevés de la journée ont été supprimés'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur lors de la suppression groupée: {str(e)}'}), 500

@app.route('/api/statistiques/<int:site_id>')
@login_required
def get_statistiques(site_id):
    jours = request.args.get('jours', 30, type=int)
    date_debut = datetime.now().date() - timedelta(days=jours)
    types_releve = TypeReleve.query.filter_by(site_id=site_id).all()
    stats = []
    for tr in types_releve:
        releves = Releve.query.filter_by(type_releve_id=tr.id).filter(Releve.date >= date_debut).all()
        if not releves:
            continue
        valeurs = [r.valeur for r in releves]
        stat = {
            'nom': tr.nom,
            'moyenne': sum(valeurs)/len(valeurs) if valeurs else 0,
            'min': min(valeurs) if valeurs else 0,
            'max': max(valeurs) if valeurs else 0,
            'total': sum(valeurs) if valeurs else 0,
            'unite': tr.unite
        }
        stats.append(stat)
    return jsonify(stats)

@app.route('/api/types_releve/<int:site_id>')
@login_required
def api_types_releve(site_id):
    types = TypeReleve.query.filter_by(site_id=site_id).all()
    result = [
        {
            'id': tr.id,
            'nom': tr.nom,
            'unite': tr.unite,
            'type_mesure': tr.type_mesure,
            'frequence': tr.frequence,
            'jour_specifique': tr.jour_specifique
        }
        for tr in types
    ]
    return jsonify(result)

@app.route('/api/indicateurs_donnee/<int:type_releve_id>')
@login_required
def api_indicateurs_donnee(type_releve_id):
    jours = request.args.get('jours', 30, type=int)
    date_debut = datetime.now().date() - timedelta(days=jours)
    type_releve = TypeReleve.query.get_or_404(type_releve_id)
    try:
        if type_releve.type_mesure == 'totalisateur':
            releves = Releve.query.filter_by(type_releve_id=type_releve_id).filter(Releve.date >= date_debut).order_by(Releve.date).all()
            valeurs = []
            if len(releves) > 1:
                for i in range(1, len(releves)):
                    difference = releves[i].valeur - releves[i-1].valeur
                    valeurs.append({
                        'date': releves[i].date.strftime('%Y-%m-%d'),
                        'valeur': difference
                    })
            print(f"[API indicateurs_donnee] type={type_releve.nom} valeurs={valeurs}")
            return jsonify([{
                'nom': type_releve.nom,
                'unite': type_releve.unite,
                'valeurs': valeurs
            }])
        else:
            releves = Releve.query.filter_by(type_releve_id=type_releve_id).filter(Releve.date >= date_debut).order_by(Releve.date).all()
            valeurs = [
                {'date': r.date.strftime('%Y-%m-%d'), 'valeur': r.valeur}
                for r in releves
            ]
            print(f"[API indicateurs_donnee] type={type_releve.nom} valeurs={valeurs}")
            return jsonify([{
                'nom': type_releve.nom,
                'unite': type_releve.unite,
                'valeurs': valeurs
            }])
    except Exception as e:
        print(f"[API indicateurs_donnee] ERREUR: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/rapport_pdf')
@login_required
def rapport_pdf():
    # Récupérer les paramètres
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    sites_param = request.args.get('sites')  # ex: "SMP,LPZ"
    if not date_debut or not date_fin or not sites_param:
        return "Paramètres manquants", 400
    try:
        date_debut_dt = datetime.strptime(date_debut, '%Y-%m-%d').date()
        date_fin_dt = datetime.strptime(date_fin, '%Y-%m-%d').date()
    except Exception:
        return "Format de date invalide", 400
    site_noms = sites_param.split(',')
    sites = Site.query.filter(Site.nom.in_(site_noms)).all()
    if not sites:
        return "Aucun site trouvé", 400

    # Récupérer tous les types de relevé pour les sites sélectionnés
    types_releves = TypeReleve.query.filter(TypeReleve.site_id.in_([s.id for s in sites])).all()

    # Récupérer les données pour chaque type de relevé
    data_series = []
    for tr in types_releves:
        releves = Releve.query.filter_by(type_releve_id=tr.id).filter(
            Releve.date >= date_debut_dt, Releve.date <= date_fin_dt
        ).order_by(Releve.date).all()
        if not releves:
            continue
        if tr.type_mesure == 'totalisateur' and len(releves) > 1:
            valeurs = []
            for i in range(1, len(releves)):
                difference = releves[i].valeur - releves[i-1].valeur
                valeurs.append((releves[i].date, difference))
        else:
            valeurs = [(r.date, r.valeur) for r in releves]
        data_series.append({
            'nom': tr.nom,
            'site': Site.query.get(tr.site_id).nom,
            'unite': tr.unite,
            'valeurs': valeurs
        })

    # Générer les graphiques avec matplotlib et les stocker en mémoire
    images = []
    for serie in data_series:
        # Toujours générer un graphique, même si pas de valeurs
        if serie['valeurs']:
            dates = [d.strftime('%d/%m/%Y') for d, v in serie['valeurs']]
            valeurs = [v for d, v in serie['valeurs']]
        else:
            dates = []
            valeurs = []
        plt.figure(figsize=(6,3))
        if valeurs:
            plt.plot(dates, valeurs, marker='o')
        else:
            plt.text(0.5, 0.5, 'Aucune donnée pour cette période', ha='center', va='center', fontsize=12, color='red', transform=plt.gca().transAxes)
        plt.title(f"{serie['nom']} - {serie['site']}")
        plt.xlabel('Date')
        plt.ylabel(f"Valeur ({serie['unite']})")
        plt.xticks(rotation=45, fontsize=7)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        images.append(buf.read())

    # Générer le PDF avec fpdf
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font('Arial', 'B', 16)
    pdf.add_page()
    pdf.cell(0, 10, f"Rapport des relevés STE", ln=1, align='C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f"Période : {date_debut} au {date_fin}", ln=1, align='C')
    pdf.cell(0, 10, f"Site(s) : {', '.join(site_noms)}", ln=1, align='C')
    pdf.ln(5)
    # 3 graphiques par page
    for i, img in enumerate(images):
        if i % 3 == 0 and i != 0:
            pdf.add_page()
        # Sauvegarder l'image temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
            tmp_img.write(img)
            tmp_img_path = tmp_img.name
        pdf.image(tmp_img_path, x=15, y=pdf.get_y(), w=180)
        pdf.ln(65)
        os.remove(tmp_img_path)
    # Retourner le PDF
    pdf_out = io.BytesIO()
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin1')
    pdf_out.write(pdf_bytes)
    pdf_out.seek(0)
    return send_file(pdf_out, mimetype='application/pdf', as_attachment=False, download_name='rapport_releves.pdf')

@app.route('/attente_rapport_pdf')
def attente_rapport_pdf():
    return render_template('attente_rapport_pdf.html')

# Routes pour les routines d'exploitation
@app.route('/routines')
@login_required
def routines():
    return render_template('routines.html')

@app.route('/admin_routines')
@login_required
def admin_routines():
    if current_user.role != 'admin':
        flash('Accès non autorisé')
        return redirect(url_for('index'))
    return render_template('admin_routines.html')

@app.route('/remplir_routine/<int:formulaire_id>')
@login_required
def remplir_routine(formulaire_id):
    return render_template('remplir_routine.html', formulaire_id=formulaire_id)

@app.route('/recap_routines')
@login_required
def recap_routines():
    return render_template('recap_routines.html')

@app.route('/detail_routine/<int:formulaire_id>')
@login_required
def detail_routine(formulaire_id):
    return render_template('detail_routine.html', formulaire_id=formulaire_id)

# API Routes pour les routines
@app.route('/api/routines/formulaires')
@login_required
def api_formulaires():
    formulaires = FormulaireRoutine.query.order_by(FormulaireRoutine.nom).all()
    return jsonify([{
        'id': f.id,
        'nom': f.nom,
        'created_at': f.created_at.isoformat() if f.created_at else None
    } for f in formulaires])

@app.route('/api/routines/formulaires/<int:formulaire_id>/questions')
@login_required
def api_questions_formulaire(formulaire_id):
    questions = QuestionRoutine.query.filter_by(formulaire_id=formulaire_id).order_by(QuestionRoutine.lieu, QuestionRoutine.ordre, QuestionRoutine.id_question).all()
    return jsonify([{
        'id': q.id,
        'id_question': q.id_question,
        'lieu': q.lieu,
        'question': q.question,
        'ordre': q.ordre
    } for q in questions])

@app.route('/api/routines/import-excel', methods=['POST'])
@login_required
def api_import_excel():
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    file = request.files['file']
    formulaire_id = request.form.get('formulaireId')
    
    if not file or not formulaire_id:
        return jsonify({'error': 'Fichier et ID du formulaire requis'}), 400
    
    try:
        # Lire le fichier Excel
        df = pd.read_excel(file)
        
        if not all(col in df.columns for col in ['id', 'lieu', 'question']):
            return jsonify({'error': 'Le fichier doit contenir les colonnes: id, lieu, question'}), 400
        
        updated_count = 0
        inserted_count = 0
        
        for index, row in df.iterrows():
            if pd.notna(row['id']) and pd.notna(row['lieu']) and pd.notna(row['question']):
                id_question = str(row['id'])
                
                # Vérifier si la question existe déjà
                question_existante = QuestionRoutine.query.filter_by(
                    formulaire_id=formulaire_id,
                    id_question=id_question
                ).first()
                
                if question_existante:
                    # Mettre à jour
                    question_existante.lieu = row['lieu']
                    question_existante.question = row['question']
                    question_existante.ordre = index + 1
                    updated_count += 1
                else:
                    # Créer nouvelle question
                    nouvelle_question = QuestionRoutine(
                        formulaire_id=formulaire_id,
                        id_question=id_question,
                        lieu=row['lieu'],
                        question=row['question'],
                        ordre=index + 1
                    )
                    db.session.add(nouvelle_question)
                    inserted_count += 1
        
        db.session.commit()
        return jsonify({
            'message': 'Import réussi',
            'updated': updated_count,
            'inserted': inserted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de l\'import: {str(e)}'}), 500

@app.route('/api/routines/reponses', methods=['POST'])
@login_required
def api_sauvegarder_reponse():
    data = request.form.to_dict()
    formulaire_id = data.get('formulaireId')
    question_id = data.get('questionId')
    reponse = data.get('reponse')
    commentaire = data.get('commentaire', '')
    
    if not all([formulaire_id, question_id, reponse]):
        return jsonify({'error': 'Données manquantes'}), 400
    
    # Gérer l'upload de photo
    photo_path = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename:
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_path = filename
    
    # Créer la réponse
    nouvelle_reponse = ReponseRoutine(
        formulaire_id=formulaire_id,
        question_id=question_id,
        reponse=reponse,
        commentaire=commentaire,
        photo_path=photo_path,
        utilisateur_id=current_user.id
    )
    
    db.session.add(nouvelle_reponse)
    db.session.commit()
    
    return jsonify({
        'id': nouvelle_reponse.id,
        'message': 'Réponse enregistrée'
    })

@app.route('/api/routines/reponses/<date>')
@login_required
def api_reponses_date(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400
    
    reponses = db.session.query(ReponseRoutine, QuestionRoutine, FormulaireRoutine).join(
        QuestionRoutine, ReponseRoutine.question_id == QuestionRoutine.id
    ).join(
        FormulaireRoutine, ReponseRoutine.formulaire_id == FormulaireRoutine.id
    ).filter(
        ReponseRoutine.date_creation == date_obj
    ).order_by(ReponseRoutine.heure_creation.desc()).all()
    
    result = []
    for reponse, question, formulaire in reponses:
        result.append({
            'id': reponse.id,
            'formulaire_id': reponse.formulaire_id,
            'formulaire_nom': formulaire.nom,
            'question_id': reponse.question_id,
            'id_question': question.id_question,
            'lieu': question.lieu,
            'question': question.question,
            'reponse': reponse.reponse,
            'commentaire': reponse.commentaire,
            'photo_path': reponse.photo_path,
            'date_creation': reponse.date_creation.isoformat(),
            'heure_creation': reponse.heure_creation.isoformat() if reponse.heure_creation else None
        })
    
    return jsonify(result)

@app.route('/api/routines/reponses/<int:reponse_id>', methods=['PUT'])
@login_required
def api_modifier_reponse(reponse_id):
    reponse = ReponseRoutine.query.get(reponse_id)
    if not reponse:
        return jsonify({'error': 'Réponse non trouvée'}), 404
    
    # Vérifier que la réponse date d'aujourd'hui
    if reponse.date_creation != datetime.now().date():
        return jsonify({'error': 'Modification non autorisée'}), 403
    
    data = request.form.to_dict()
    reponse.reponse = data.get('reponse', reponse.reponse)
    reponse.commentaire = data.get('commentaire', reponse.commentaire)
    
    # Gérer l'upload de nouvelle photo
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename:
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            reponse.photo_path = filename
    
    db.session.commit()
    return jsonify({'message': 'Réponse modifiée'})

@app.route('/api/routines/reponses/<int:reponse_id>', methods=['DELETE'])
@login_required
def api_supprimer_reponse(reponse_id):
    reponse = ReponseRoutine.query.get(reponse_id)
    if not reponse:
        return jsonify({'error': 'Réponse non trouvée'}), 404
    
    # Vérifier que la réponse date d'aujourd'hui
    if reponse.date_creation != datetime.now().date():
        return jsonify({'error': 'Suppression non autorisée'}), 403
    
    db.session.delete(reponse)
    db.session.commit()
    return jsonify({'message': 'Réponse supprimée'})

@app.route('/api/routines/export-pdf/<date>')
@login_required
def api_export_pdf_routines(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400
    
    reponses = db.session.query(ReponseRoutine, QuestionRoutine, FormulaireRoutine).join(
        QuestionRoutine, ReponseRoutine.question_id == QuestionRoutine.id
    ).join(
        FormulaireRoutine, ReponseRoutine.formulaire_id == FormulaireRoutine.id
    ).filter(
        ReponseRoutine.date_creation == date_obj
    ).order_by(FormulaireRoutine.nom, QuestionRoutine.lieu, QuestionRoutine.id_question).all()
    
    # Créer le PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Rapport des Routines STE', ln=1, align='C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'Date: {date}', ln=1, align='C')
    pdf.ln(10)
    
    # Grouper par formulaire
    grouped_by_form = {}
    for reponse, question, formulaire in reponses:
        if formulaire.nom not in grouped_by_form:
            grouped_by_form[formulaire.nom] = []
        grouped_by_form[formulaire.nom].append((reponse, question))
    
    for form_name, form_reponses in grouped_by_form.items():
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, form_name, ln=1)
        pdf.ln(5)
        
        # Grouper par lieu
        grouped_by_lieu = {}
        for reponse, question in form_reponses:
            if question.lieu not in grouped_by_lieu:
                grouped_by_lieu[question.lieu] = []
            grouped_by_lieu[question.lieu].append((reponse, question))
        
        for lieu, lieu_reponses in grouped_by_lieu.items():
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, f'Question {question.id_question}: {question.question}')
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 5, f'Réponse: {reponse.reponse}', ln=1)
            if reponse.commentaire:
                pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 4, f'Commentaire: {reponse.commentaire}')
            pdf.ln(3)
        
        pdf.ln(5)
    
    # Retourner le PDF
    pdf_out = io.BytesIO()
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin1')
    pdf_out.write(pdf_bytes)
    pdf_out.seek(0)
    
    return send_file(
        pdf_out,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'rapport-routines-{date}.pdf'
    )

@app.route('/api/routines/export-excel/<date>')
@login_required
def api_export_excel_routines(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400
    
    reponses = db.session.query(ReponseRoutine, QuestionRoutine, FormulaireRoutine).join(
        QuestionRoutine, ReponseRoutine.question_id == QuestionRoutine.id
    ).join(
        FormulaireRoutine, ReponseRoutine.formulaire_id == FormulaireRoutine.id
    ).filter(
        ReponseRoutine.date_creation == date_obj
    ).order_by(FormulaireRoutine.nom, QuestionRoutine.lieu, QuestionRoutine.id_question).all()
    
    # Créer le DataFrame
    data = []
    for reponse, question, formulaire in reponses:
        data.append({
            'Formulaire': formulaire.nom,
            'Lieu': question.lieu,
            'ID Question': question.id_question,
            'Question': question.question,
            'Réponse': reponse.reponse,
            'Commentaire': reponse.commentaire or '',
            'Heure': reponse.heure_creation.isoformat() if reponse.heure_creation else ''
        })
    
    df = pd.DataFrame(data)
    
    # Créer le fichier Excel temporaire
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Rapport', index=False)
    
    return send_file(
        tmp_file.name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'rapport-routines-{date}.xlsx'
    )

@app.route('/api/routines/stats/<date>')
@login_required
def api_stats_routines(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Format de date invalide'}), 400
    
    # Récupérer toutes les questions avec leurs réponses pour la date
    stats = db.session.query(
        QuestionRoutine.id_question,
        QuestionRoutine.question,
        QuestionRoutine.lieu,
        FormulaireRoutine.nom.label('formulaire_nom'),
        func.count(case((ReponseRoutine.reponse == 'Fait', 1))).label('fait'),
        func.count(case((ReponseRoutine.reponse == 'Non Fait', 1))).label('non_fait'),
        func.count(case((ReponseRoutine.reponse == 'Non Applicable', 1))).label('non_applicable'),
        func.count(ReponseRoutine.id).label('total')
    ).join(
        FormulaireRoutine, QuestionRoutine.formulaire_id == FormulaireRoutine.id
    ).outerjoin(
        ReponseRoutine, 
        db.and_(
            QuestionRoutine.id == ReponseRoutine.question_id,
            ReponseRoutine.date_creation == date_obj
        )
    ).group_by(
        QuestionRoutine.id,
        QuestionRoutine.id_question,
        QuestionRoutine.question,
        QuestionRoutine.lieu,
        FormulaireRoutine.nom
    ).order_by(
        FormulaireRoutine.nom,
        QuestionRoutine.lieu,
        QuestionRoutine.id_question
    ).all()
    
    result = []
    for stat in stats:
        result.append({
            'id_question': stat.id_question,
            'question': stat.question,
            'lieu': stat.lieu,
            'formulaire_nom': stat.formulaire_nom,
            'fait': stat.fait,
            'non_fait': stat.non_fait,
            'non_applicable': stat.non_applicable,
            'total': stat.total
        })
    
    return jsonify(result)

@app.route('/api/routines/export-excel/formulaire/<int:formulaire_id>')
@login_required
def api_export_excel_formulaire(formulaire_id):
    reponses = db.session.query(ReponseRoutine, QuestionRoutine, FormulaireRoutine).join(
        QuestionRoutine, ReponseRoutine.question_id == QuestionRoutine.id
    ).join(
        FormulaireRoutine, ReponseRoutine.formulaire_id == FormulaireRoutine.id
    ).filter(
        ReponseRoutine.formulaire_id == formulaire_id
    ).order_by(ReponseRoutine.date_creation.desc(), QuestionRoutine.lieu, QuestionRoutine.id_question).all()

    # Créer le DataFrame
    data = []
    for reponse, question, formulaire in reponses:
        data.append({
            'Date': reponse.date_creation.isoformat() if reponse.date_creation else '',
            'Heure': reponse.heure_creation.isoformat() if reponse.heure_creation else '',
            'Lieu': question.lieu,
            'ID Question': question.id_question,
            'Question': question.question,
            'Réponse': reponse.reponse,
            'Commentaire': reponse.commentaire or '',
            'Utilisateur': reponse.utilisateur_id,
            'Photo': reponse.photo_path or ''
        })

    df = pd.DataFrame(data)

    # Créer le fichier Excel temporaire
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Réponses', index=False)

    return send_file(
        tmp_file.name,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'export-formulaire-{formulaire_id}.xlsx'
    )

@app.route('/api/routines/formulaires_remplis_aujourdhui')
@login_required
def api_formulaires_remplis_aujourdhui():
    today = datetime.now().date()
    count = db.session.query(ReponseRoutine.formulaire_id).filter(ReponseRoutine.date_creation == today).distinct().count()
    return jsonify({'formulaires_remplis': count})

# Initialisation de la base de données
def init_db():
    with app.app_context():
        db.create_all()
        
        # Migration : ajouter session_id aux photos existantes si nécessaire
        try:
            # Vérifier si la colonne session_id existe
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('photo_releve')]
            
            if 'session_id' not in columns:
                print("Migration : ajout de la colonne session_id...")
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text('ALTER TABLE photo_releve ADD COLUMN session_id VARCHAR(50)'))
                        conn.commit()
                    
                    # Générer des session_id pour les photos existantes
                    photos = PhotoReleve.query.all()
                    for photo in photos:
                        timestamp = photo.created_at.strftime('%Y%m%d_%H%M%S') if photo.created_at else datetime.now().strftime('%Y%m%d_%H%M%S')
                        session_id = f"{photo.utilisateur_id}_{photo.site_id}_{timestamp}"
                        photo.session_id = session_id
                    
                    db.session.commit()
                    print(f"Migration terminée : {len(photos)} photos mises à jour")
                except Exception as e:
                    print(f"Erreur lors de l'ajout de la colonne : {e}")
                    # Si la colonne existe déjà, on continue
                    pass
            else:
                print("Colonne session_id déjà présente")
        except Exception as e:
            print(f"Erreur lors de la vérification de la migration : {e}")
        
        # Créer les sites
        if not Site.query.first():
            smp = Site(nom='SMP', description='Station de traitement des eaux SMP')
            lpz = Site(nom='LPZ', description='Station de traitement des eaux LPZ')
            db.session.add(smp)
            db.session.add(lpz)
            db.session.commit()
            
            # Créer les types de relevés pour SMP
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
                ('Boue STE', 'basique', 'kg', 'quotidien'),
                ('Boue STE CAB', 'basique', 'kg', 'quotidien'),
                ('pH entrée', 'basique', '', 'quotidien'),
                ('pH sortie', 'basique', '', 'quotidien'),
                ('Température entrée', 'basique', '°C', 'quotidien'),
                ('Température sortie', 'basique', '°C', 'quotidien'),
                ('Conductivité sortie', 'basique', 'µS/cm', 'quotidien'),
                ('MES entrée', 'basique', 'mg/L', 'quotidien'),
                ('MES sortie', 'basique', 'mg/L', 'quotidien'),
                ('Coagulant', 'basique', 'L', 'hebdomadaire', 'lundi'),
                ('Floculant', 'basique', 'L', 'quotidien'),
                ('CO2', 'basique', 'kg', 'quotidien')
            ]
            
            for nom, type_mesure, unite, frequence, *args in types_smp:
                jour_specifique = args[0] if args else None
                tr = TypeReleve(
                    nom=nom,
                    site_id=smp.id,
                    type_mesure=type_mesure,
                    unite=unite,
                    frequence=frequence,
                    jour_specifique=jour_specifique
                )
                db.session.add(tr)
            
            # Créer les types de relevés pour LPZ
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
                ('Boue STE', 'basique', 'kg', 'quotidien'),
                ('Boue STE CAB', 'basique', 'kg', 'quotidien'),
                ('pH entrée', 'basique', '', 'quotidien'),
                ('pH sortie', 'basique', '', 'quotidien'),
                ('Température entrée', 'basique', '°C', 'quotidien'),
                ('Température sortie', 'basique', '°C', 'quotidien'),
                ('Conductivité sortie', 'basique', 'µS/cm', 'quotidien'),
                ('MES entrée', 'basique', 'mg/L', 'quotidien'),
                ('MES sortie', 'basique', 'mg/L', 'quotidien'),
                ('Coagulant', 'basique', 'L', 'hebdomadaire', 'lundi'),
                ('Floculant', 'basique', 'L', 'quotidien'),
                ('CO2', 'basique', 'kg', 'quotidien')
            ]
            
            for nom, type_mesure, unite, frequence, *args in types_lpz:
                jour_specifique = args[0] if args else None
                tr = TypeReleve(
                    nom=nom,
                    site_id=lpz.id,
                    type_mesure=type_mesure,
                    unite=unite,
                    frequence=frequence,
                    jour_specifique=jour_specifique
                )
                db.session.add(tr)
            
            # Créer l'utilisateur admin s'il n'existe pas
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User()
                admin.username = 'admin'
                admin.password_hash = generate_password_hash('admin123')
                admin.role = 'admin'
                db.session.add(admin)
            
            db.session.commit()

        # Initialiser les formulaires de routines par défaut
        formulaires_routines = [
            'STE PRINCIPALE LPZ', 'STE CAB LPZ', 'STEP LPZ', 
            'STE PRINCIPALE SMP', 'STE CAB SMP', 'STEP SMP'
        ]
        
        for nom in formulaires_routines:
            formulaire_existant = FormulaireRoutine.query.filter_by(nom=nom).first()
            if not formulaire_existant:
                nouveau_formulaire = FormulaireRoutine(nom=nom)
                db.session.add(nouveau_formulaire)
        
        db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000) 