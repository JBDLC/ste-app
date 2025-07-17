# Correction du problème des commentaires dans les routines

## Problème identifié

Lorsqu'un utilisateur ajoutait un commentaire à une réponse de routine, toutes les réponses précédentes non sauvegardées disparaissaient de l'interface. Ce problème ne se produisait qu'en production (Render) et pas en local.

## Cause du problème

Le problème venait de la fonction `sauvegarderReponse()` dans `templates/remplir_routine.html`. Après avoir sauvegardé un commentaire, la fonction appelait `chargerReponses()` qui rechargeait toutes les réponses depuis la base de données.

La fonction `chargerReponses()` commençait par faire `reponses = {}` ce qui vidait complètement l'objet `reponses` avant de le remplir avec les données de la base. Cela effaçait toutes les réponses non encore sauvegardées.

## Solution implémentée

### 1. Modification de `chargerReponses()`

```javascript
function chargerReponses() {
    const aujourdhui = new Date().toISOString().split('T')[0];
    fetch(`/api/routines/reponses/${aujourdhui}`)
        .then(response => response.json())
        .then(data => {
            // Préserver les réponses locales non sauvegardées
            const reponsesLocales = { ...reponses };
            
            // Réinitialiser avec les données de la base
            reponses = {};
            data.forEach(reponse => {
                if (reponse.formulaire_id == formulaireId) {
                    reponses[reponse.question_id] = reponse;
                }
            });
            
            // Restaurer les réponses locales qui n'ont pas d'ID (non sauvegardées)
            Object.keys(reponsesLocales).forEach(questionId => {
                const reponseLocale = reponsesLocales[questionId];
                if (!reponseLocale.id || reponseLocale.id === 'undefined') {
                    reponses[questionId] = reponseLocale;
                }
            });
            
            afficherQuestions();
        })
        .catch(error => {
            console.error('Erreur lors du chargement des réponses:', error);
        });
}
```

### 2. Modification de `sauvegarderReponse()`

```javascript
function sauvegarderReponse() {
    const questionId = document.getElementById('modal-question-id').value;
    const formulaireId = document.getElementById('modal-formulaire-id').value;
    const commentaire = document.getElementById('modal-commentaire').value;
    
    const formData = new FormData();
    formData.append('reponse', reponses[questionId].reponse);
    formData.append('commentaire', commentaire);
    
    // Correction : POST si pas d'ID, PUT sinon
    const repId = reponses[questionId] && reponses[questionId].id;
    let url, method;
    if (repId && repId !== 'undefined') {
        url = `/api/routines/reponses/${repId}`;
        method = 'PUT';
    } else {
        url = '/api/routines/reponses';
        method = 'POST';
        formData.append('formulaireId', formulaireId);
        formData.append('questionId', questionId);
    }
    fetch(url, {
        method: method,
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Erreur : ' + data.error);
        } else {
            // Mettre à jour la réponse locale avec l'ID retourné
            if (data.id) {
                reponses[questionId].id = data.id;
            }
            reponses[questionId].commentaire = commentaire;
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('detailModal'));
            modal.hide();
            
            // Recharger seulement cette réponse depuis la base pour avoir les données complètes
            chargerReponseUnique(questionId);
        }
    })
    .catch(error => {
        console.error('Erreur lors de la modification:', error);
        alert('Erreur lors de la modification');
    });
}
```

### 3. Nouvelle fonction `chargerReponseUnique()`

```javascript
// Nouvelle fonction pour charger une seule réponse
function chargerReponseUnique(questionId) {
    const aujourdhui = new Date().toISOString().split('T')[0];
    fetch(`/api/routines/reponses/${aujourdhui}`)
        .then(response => response.json())
        .then(data => {
            // Trouver la réponse pour cette question
            const reponse = data.find(r => r.question_id == questionId && r.formulaire_id == formulaireId);
            if (reponse) {
                // Mettre à jour seulement cette réponse dans l'objet local
                reponses[questionId] = reponse;
                afficherQuestions();
            }
        })
        .catch(error => {
            console.error('Erreur lors du chargement de la réponse:', error);
        });
}
```

## Améliorations apportées

1. **Préservation des réponses locales** : Les réponses non encore sauvegardées sont préservées lors du rechargement
2. **Rechargement ciblé** : Après l'ajout d'un commentaire, seule la réponse modifiée est rechargée
3. **Mise à jour locale** : L'ID de la réponse est mis à jour localement après sauvegarde
4. **Gestion d'erreurs améliorée** : Meilleure gestion des erreurs avec messages explicites

## Fichiers modifiés

- `templates/remplir_routine.html` : Correction des fonctions JavaScript

## Test de validation

Un script de test `test_routines_commentaires.py` a été créé pour valider que le problème est résolu.

## Déploiement

Pour appliquer cette correction sur Render :

1. Mettre à jour le fichier `templates/remplir_routine.html` sur Render
2. Redémarrer l'application si nécessaire

## Résultat attendu

- Les commentaires peuvent être ajoutés sans perdre les réponses précédentes
- L'interface reste cohérente entre les sessions
- Le problème ne se reproduit plus en production 