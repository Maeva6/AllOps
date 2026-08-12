import os
import re
import shutil
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from app.extensions import db
from app.models import FileOperation, OrganisationSnapshot
import json

files_bp = Blueprint('files', __name__, url_prefix='/files')

# ─── Page principale ──────────────────────────────────────────────────────────
@files_bp.route('/')
def index():
    operations = FileOperation.query.order_by(
        FileOperation.created_at.desc()
    ).limit(20).all()   # ← 10 → 20
    return render_template('modules/files.html',
                           title="Gestion des Fichiers",
                           operations=operations)


# ─── 1. Renommage en masse ────────────────────────────────────────────────────
# @files_bp.route('/renommer', methods=['POST'])
# def renommer():
#     dossier  = request.form.get('dossier', '').strip()
#     prefixe  = request.form.get('prefixe', '').strip()
#     suffixe  = request.form.get('suffixe', '').strip()
#     extension = request.form.get('extension', '').strip().lower()

#     # Vérifications
#     if not dossier:
#         flash('Veuillez indiquer un dossier.', 'danger')
#         return redirect(url_for('files.index'))

#     if not os.path.isdir(dossier):
#         flash(f'Dossier introuvable : {dossier}', 'danger')
#         return redirect(url_for('files.index'))

#     # Lister les fichiers
#     fichiers = [
#         f for f in os.listdir(dossier)
#         if os.path.isfile(os.path.join(dossier, f))
#         and not f.startswith('.')
#     ]

#     if extension:
#         fichiers = [f for f in fichiers if f.endswith(extension)]

#     if not fichiers:
#         flash('Aucun fichier trouvé dans ce dossier.', 'warning')
#         return redirect(url_for('files.index'))

#     # Renommer
#     compteur = 0
#     date_str = datetime.now().strftime('%Y-%m-%d')

#     for i, fichier in enumerate(sorted(fichiers), start=1):
#         ext_fichier = os.path.splitext(fichier)[1]
#         nouveau_nom = f"{prefixe}_{date_str}_{i:02d}{suffixe}{ext_fichier}"
#         ancien_path = os.path.join(dossier, fichier)
#         nouveau_path = os.path.join(dossier, nouveau_nom)

#         try:
#             os.rename(ancien_path, nouveau_path)
#             compteur += 1
#         except Exception as e:
#             flash(f'Erreur sur {fichier} : {str(e)}', 'danger')

#     # Sauvegarder dans la base
#     op = FileOperation(
#         type_op='rename',
#         nb_fichiers=compteur,
#         details=f"Dossier: {dossier} | Préfixe: {prefixe} | {compteur} fichiers renommés",
#         statut='success'
#     )
#     db.session.add(op)
#     db.session.commit()

#     flash(f'✅ {compteur} fichier(s) renommé(s) avec succès !', 'success')
#     return redirect(url_for('files.index'))


# # ─── 2. Fusion de PDFs ────────────────────────────────────────────────────────
# @files_bp.route('/fusionner-pdf', methods=['POST'])
# def fusionner_pdf():
#     try:
#         import fitz  # PyMuPDF
#     except ImportError:
#         flash('PyMuPDF non installé.', 'danger')
#         return redirect(url_for('files.index'))

#     dossier  = request.form.get('dossier_pdf', '').strip()
#     nom_sortie = request.form.get('nom_sortie', 'fusion_output').strip()

#     if not os.path.isdir(dossier):
#         flash(f'Dossier introuvable : {dossier}', 'danger')
#         return redirect(url_for('files.index'))

#     # Lister les PDFs
#     pdfs = sorted([
#         f for f in os.listdir(dossier)
#         if f.lower().endswith('.pdf')
#     ])

#     if len(pdfs) < 2:
#         flash('Il faut au moins 2 fichiers PDF dans le dossier.', 'warning')
#         return redirect(url_for('files.index'))

#     # Fusionner
#     doc_final = fitz.open()
#     for pdf in pdfs:
#         chemin = os.path.join(dossier, pdf)
#         doc = fitz.open(chemin)
#         doc_final.insert_pdf(doc)
#         doc.close()

#     # Sauvegarder
#     if not nom_sortie.endswith('.pdf'):
#         nom_sortie += '.pdf'
#     chemin_sortie = os.path.join(dossier, nom_sortie)
#     doc_final.save(chemin_sortie)
#     doc_final.close()

#     # Log en base
#     op = FileOperation(
#         type_op='merge_pdf',
#         nb_fichiers=len(pdfs),
#         details=f"{len(pdfs)} PDFs fusionnés → {nom_sortie}",
#         statut='success'
#     )
#     db.session.add(op)
#     db.session.commit()

#     flash(f'✅ {len(pdfs)} PDFs fusionnés → {nom_sortie}', 'success')
#     return redirect(url_for('files.index'))

@files_bp.route('/renommer', methods=['POST'])
def renommer():
    dossier   = request.form.get('dossier', '').strip()
    prefixe   = request.form.get('prefixe', '').strip()
    suffixe   = request.form.get('suffixe', '').strip()
    extension = request.form.get('extension', '').strip().lower()

    if not os.path.isdir(dossier):
        flash(f'Dossier introuvable : {dossier}', 'danger')
        return redirect(url_for('files.index'))

    fichiers = [
        f for f in os.listdir(dossier)
        if os.path.isfile(os.path.join(dossier, f))
        and not f.startswith('.')
    ]
    if extension:
        fichiers = [f for f in fichiers if f.endswith(extension)]

    if not fichiers:
        flash('Aucun fichier trouvé.', 'warning')
        return redirect(url_for('files.index'))

    mouvements = []
    date_str   = datetime.now().strftime('%Y-%m-%d')

    for i, fichier in enumerate(sorted(fichiers), start=1):
        ext_f       = os.path.splitext(fichier)[1]
        nouveau_nom = f"{prefixe}_{date_str}_{i:02d}{suffixe}{ext_f}"
        src         = os.path.join(dossier, fichier)
        dst         = os.path.join(dossier, nouveau_nom)

        try:
            os.rename(src, dst)
            mouvements.append({'origine': src, 'destination': dst})
        except Exception as e:
            flash(f'Erreur sur {fichier} : {str(e)}', 'danger')

    op = FileOperation(
        type_op       = 'rename',
        nb_fichiers   = len(mouvements),
        details       = f"Dossier: {dossier} | Préfixe: {prefixe}",
        statut        = 'success',
        annule        = False,
        rollback_data = json.dumps(mouvements)
    )
    db.session.add(op)
    db.session.commit()

    flash(
        f'✅ {len(mouvements)} fichier(s) renommé(s). '
        f'<a href="{url_for("files.rollback", id=op.id)}" '
        f'class="alert-link">↩️ Annuler</a>',
        'success'
    )
    return redirect(url_for('files.index'))


@files_bp.route('/fusionner-pdf', methods=['POST'])
def fusionner_pdf():
    try:
        import fitz
    except ImportError:
        flash('PyMuPDF non installé.', 'danger')
        return redirect(url_for('files.index'))

    dossier    = request.form.get('dossier_pdf', '').strip()
    nom_sortie = request.form.get('nom_sortie', 'fusion_output').strip()

    if not os.path.isdir(dossier):
        flash(f'Dossier introuvable : {dossier}', 'danger')
        return redirect(url_for('files.index'))

    pdfs = sorted([
        f for f in os.listdir(dossier)
        if f.lower().endswith('.pdf')
    ])

    if len(pdfs) < 2:
        flash('Il faut au moins 2 fichiers PDF.', 'warning')
        return redirect(url_for('files.index'))

    if not nom_sortie.endswith('.pdf'):
        nom_sortie += '.pdf'

    chemin_sortie = os.path.join(dossier, nom_sortie)

    doc_final = fitz.open()
    for pdf in pdfs:
        doc = fitz.open(os.path.join(dossier, pdf))
        doc_final.insert_pdf(doc)
        doc.close()
    doc_final.save(chemin_sortie)
    doc_final.close()

    # Rollback = supprimer le fichier créé
    rollback = {'fichier_cree': chemin_sortie}

    op = FileOperation(
        type_op       = 'merge_pdf',
        nb_fichiers   = len(pdfs),
        details       = f"{len(pdfs)} PDFs fusionnés → {nom_sortie}",
        statut        = 'success',
        annule        = False,
        rollback_data = json.dumps(rollback)
    )
    db.session.add(op)
    db.session.commit()

    flash(
        f'✅ {len(pdfs)} PDFs fusionnés → {nom_sortie}. '
        f'<a href="{url_for("files.rollback", id=op.id)}" '
        f'class="alert-link">↩️ Annuler</a>',
        'success'
    )
    return redirect(url_for('files.index'))


# ─── Rollback universel (rename + fusion + organisation) ─────────────────────
@files_bp.route('/rollback/<int:id>')
def rollback(id):
    op = db.session.get(FileOperation, id)
    if not op:
        abort(404)

    if op.annule:
        flash('⚠️ Cette action a déjà été annulée.', 'warning')
        return redirect(url_for('files.index'))

    data    = op.get_rollback_data()
    erreurs = []
    succes  = 0

    # ── Rollback renommage ────────────────────────────────────────────────────
    if op.type_op == 'rename':
        for mv in data:
            src = mv['destination']
            dst = mv['origine']
            if not os.path.exists(src):
                erreurs.append(os.path.basename(src))
                continue
            try:
                os.rename(src, dst)
                succes += 1
            except Exception as e:
                erreurs.append(str(e))

    # ── Rollback fusion PDF ───────────────────────────────────────────────────
    elif op.type_op == 'merge_pdf':
        fichier = data.get('fichier_cree')
        if fichier and os.path.exists(fichier):
            try:
                os.remove(fichier)
                succes = 1
            except Exception as e:
                erreurs.append(str(e))
        else:
            erreurs.append('Fichier fusionné introuvable')

    # ── Rollback organisation ─────────────────────────────────────────────────
    elif op.type_op == 'organize':
        # Récupérer mouvements et dossiers créés depuis le JSON
        mouvements     = data.get('mouvements', [])
        dossiers_crees = data.get('dossiers_crees', [])

        for mv in mouvements:
            src = mv['destination']
            dst = mv['origine']
            if not os.path.exists(src):
                erreurs.append(os.path.basename(src))
                continue
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    base, ext_f = os.path.splitext(os.path.basename(dst))
                    dst = os.path.join(
                        os.path.dirname(dst),
                        f"{base}_restaure_{datetime.now().strftime('%H%M%S')}{ext_f}"
                    )
                shutil.move(src, dst)
                succes += 1
            except Exception as e:
                erreurs.append(str(e))

        # Supprimer les dossiers créés (du plus profond au plus haut)
        for d in sorted(dossiers_crees, reverse=True):
            try:
                contenu_visible = [
                    f for f in os.listdir(d)
                    if not f.startswith('.')
                ]
                if os.path.isdir(d) and not contenu_visible:
                    os.rmdir(d)
            except Exception:
                pass

    op.annule = True
    db.session.commit()

    if erreurs:
        flash(
            f'↩️ Annulation partielle : {succes} OK. '
            f'Erreurs : {", ".join(erreurs[:3])}',
            'warning'
        )
    else:
        msg = {
            'rename':     f'↩️ {succes} fichier(s) remis à leur nom d\'origine.',
            'merge_pdf':  '↩️ Fichier fusionné supprimé.',
            'organize':   f'↩️ {succes} fichier(s) remis en place. Dossiers vides supprimés.',
        }
        flash(msg.get(op.type_op, '↩️ Action annulée.'), 'success')

    return redirect(url_for('files.index'))


# ─── 3. Organisation automatique ─────────────────────────────────────────────
# @files_bp.route('/organiser', methods=['POST'])
# def organiser():
#     dossier = request.form.get('dossier_org', '').strip()

#     if not os.path.isdir(dossier):
#         flash(f'Dossier introuvable : {dossier}', 'danger')
#         return redirect(url_for('files.index'))

#     # Règles de classement par extension
#     regles = {
#         'Images':     ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
#         'Documents':  ['.pdf', '.doc', '.docx', '.odt', '.txt', '.md'],
#         'Tableurs':   ['.xls', '.xlsx', '.csv', '.ods'],
#         'Slides':     ['.ppt', '.pptx', '.odp'],
#         'Archives':   ['.zip', '.tar', '.gz', '.rar', '.7z'],
#         'Code':       ['.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.sh'],
#         'Videos':     ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
#         'Audio':      ['.mp3', '.wav', '.flac', '.aac'],
#         'Autres':     []
#     }

#     compteur = 0
#     fichiers = [
#         f for f in os.listdir(dossier)
#         if os.path.isfile(os.path.join(dossier, f))
#         and not f.startswith('.')
#     ]

#     for fichier in fichiers:
#         ext = os.path.splitext(fichier)[1].lower()
#         dossier_cible = 'Autres'

#         for categorie, extensions in regles.items():
#             if ext in extensions:
#                 dossier_cible = categorie
#                 break

#         # Créer le sous-dossier si nécessaire
#         chemin_cible = os.path.join(dossier, dossier_cible)
#         os.makedirs(chemin_cible, exist_ok=True)

#         # Déplacer le fichier
#         src = os.path.join(dossier, fichier)
#         dst = os.path.join(chemin_cible, fichier)

#         # Éviter d'écraser un fichier existant
#         if os.path.exists(dst):
#             base, ext_f = os.path.splitext(fichier)
#             dst = os.path.join(chemin_cible, f"{base}_{datetime.now().strftime('%H%M%S')}{ext_f}")

#         shutil.move(src, dst)
#         compteur += 1

#     # Log en base
#     op = FileOperation(
#         type_op='organize',
#         nb_fichiers=compteur,
#         details=f"Dossier: {dossier} | {compteur} fichiers organisés",
#         statut='success'
#     )
#     db.session.add(op)
#     db.session.commit()

#     flash(f'✅ {compteur} fichier(s) organisé(s) par catégorie !', 'success')
#     return redirect(url_for('files.index'))

@files_bp.route('/organiser', methods=['POST'])
def organiser():
    dossier = request.form.get('dossier_org', '').strip()

    if not os.path.isdir(dossier):
        flash(f'Dossier introuvable : {dossier}', 'danger')
        return redirect(url_for('files.index'))

    regles = {
        'Images':    ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
        'Documents': ['.pdf', '.doc', '.docx', '.odt', '.txt', '.md'],
        'Tableurs':  ['.xls', '.xlsx', '.csv', '.ods'],
        'Slides':    ['.ppt', '.pptx', '.odp'],
        'Archives':  ['.zip', '.tar', '.gz', '.rar', '.7z'],
        'Code':      ['.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.sh'],
        'Videos':    ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
        'Audio':     ['.mp3', '.wav', '.flac', '.aac'],
        'Autres':    []
    }

    fichiers = [
        f for f in os.listdir(dossier)
        if os.path.isfile(os.path.join(dossier, f))
        and not f.startswith('.')
    ]

    if not fichiers:
        flash('Aucun fichier trouvé.', 'warning')
        return redirect(url_for('files.index'))

    mouvements      = []
    dossiers_crees  = []   # ← on enregistre les dossiers créés

    for fichier in fichiers:
        ext = os.path.splitext(fichier)[1].lower()
        categorie = 'Autres'
        for cat, extensions in regles.items():
            if ext in extensions:
                categorie = cat
                break

        chemin_cible = os.path.join(dossier, categorie)

        # Enregistrer si le dossier n'existait pas encore
        if not os.path.exists(chemin_cible):
            dossiers_crees.append(chemin_cible)

        os.makedirs(chemin_cible, exist_ok=True)

        src = os.path.join(dossier, fichier)
        dst = os.path.join(chemin_cible, fichier)

        if os.path.exists(dst):
            base, ext_f = os.path.splitext(fichier)
            dst = os.path.join(
                chemin_cible,
                f"{base}_{datetime.now().strftime('%H%M%S')}{ext_f}"
            )

        shutil.move(src, dst)
        mouvements.append({
            'origine':     src,
            'destination': dst
        })

    # Sauvegarder mouvements ET dossiers créés
    rollback_data = json.dumps({
        'mouvements':     mouvements,
        'dossiers_crees': dossiers_crees   # ← nouveau
    })

    op = FileOperation(
        type_op       = 'organize',
        nb_fichiers   = len(mouvements),
        details       = f"Dossier: {dossier} | {len(mouvements)} fichiers organisés",
        statut        = 'success',
        annule        = False,
        rollback_data = rollback_data
    )
    db.session.add(op)
    db.session.commit()

    flash(
        f'✅ {len(mouvements)} fichier(s) organisé(s). '
        f'<a href="{url_for("files.rollback", id=op.id)}" '
        f'class="alert-link">↩️ Annuler</a>',
        'success'
    )
    return redirect(url_for('files.index'))

# ─── Annuler une organisation ─────────────────────────────────────────────────
@files_bp.route('/annuler-organisation/<int:id>')
def annuler_organisation(id):
    snapshot = OrganisationSnapshot.query.get_or_404(id)

    if snapshot.annule:
        flash('⚠️ Cette organisation a déjà été annulée.', 'warning')
        return redirect(url_for('files.index'))

    mouvements = snapshot.get_mouvements()
    erreurs    = []
    succes     = 0

    for mv in mouvements:
        src = mv['destination']   # fichier là où il est maintenant
        dst = mv['origine']       # on le remet à l'origine

        if not os.path.exists(src):
            erreurs.append(f"{mv['nom_fichier']} introuvable")
            continue

        # Recréer le dossier d'origine si nécessaire
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # Éviter d'écraser un fichier existant à l'origine
        if os.path.exists(dst):
            base, ext_f = os.path.splitext(mv['nom_fichier'])
            dst = os.path.join(
                os.path.dirname(dst),
                f"{base}_restaure_{datetime.now().strftime('%H%M%S')}{ext_f}"
            )

        shutil.move(src, dst)
        succes += 1

    # Marquer comme annulé
    snapshot.annule = True
    db.session.commit()

    if erreurs:
        flash(
            f'↩️ Annulation partielle : {succes} fichier(s) restauré(s). '
            f'Erreurs : {", ".join(erreurs)}',
            'warning'
        )
    else:
        flash(
            f'↩️ Organisation annulée ! {succes} fichier(s) remis à leur place.',
            'success'
        )

    return redirect(url_for('files.index'))


# ─── Historique des organisations ─────────────────────────────────────────────
@files_bp.route('/historique')
def historique():
    page = request.args.get('page', 1, type=int)
    pagination = FileOperation.query.order_by(
        FileOperation.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    return render_template('modules/historique.html',
                           title="Historique",
                           snapshots=pagination.items,
                           pagination=pagination,
                           pagination_endpoint='files.historique')



# ─── Explorateur de dossiers ──────────────────────────────────────────────────
# @files_bp.route('/explorer')
# def explorer():
#     """Retourne le contenu d'un dossier en JSON pour l'explorateur"""
#     chemin = request.args.get('chemin', '/home/maeva')

#     # Sécurité : rester dans /home
#     if not chemin.startswith('/home'):
#         chemin = '/home/maeva','/host/desktop'  # <-- accès au desktop Windows

#     try:
#         contenu = []
#         with os.scandir(chemin) as entries:
#             for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name)):
#                 if entry.name.startswith('.'):
#                     continue
#                 contenu.append({
#                     'nom':       entry.name,
#                     'chemin':    entry.path,
#                     'est_dossier': entry.is_dir(),
#                     'taille':    entry.stat().st_size if entry.is_file() else None
#                 })

#         return json.dumps({
#             'chemin_actuel': chemin,
#             'parent':        str(os.path.dirname(chemin)),
#             'contenu':       contenu
#         })

#     except PermissionError:
#         return json.dumps({'erreur': 'Permission refusée'}), 403
#     except FileNotFoundError:
#         return json.dumps({'erreur': 'Dossier introuvable'}), 404

from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
import json

@files_bp.route('/explorer')
def explorer():
    chemin = request.args.get('chemin', '/home/maeva').strip()

    CHEMINS_AUTORISES = [
        '/home/maeva',
        '/mnt/c/Users/gaps6',
    ]

    autorise = any(chemin.startswith(base) for base in CHEMINS_AUTORISES)
    if not autorise:
        chemin = '/home/maeva'

    try:
        contenu = []
        with os.scandir(chemin) as entries:
            for entry in sorted(
                entries, key=lambda e: (not e.is_dir(), e.name.lower())
            ):
                if entry.name.startswith('.'):
                    continue
                contenu.append({
                    'nom':         entry.name,
                    'chemin':      entry.path,
                    'est_dossier': entry.is_dir(),
                    'taille':      entry.stat().st_size if entry.is_file() else None
                })

        raccourcis = [
            {'nom': '🏠 Home WSL',          'chemin': '/home/maeva'},
            {'nom': '🖥️ Bureau Windows',    'chemin': '/mnt/c/Users/gaps6/Desktop'},
            {'nom': '📁 Documents',          'chemin': '/mnt/c/Users/gaps6/Documents'},
            {'nom': '⬇️ Téléchargements',   'chemin': '/mnt/c/Users/gaps6/Downloads'},
        ]

        return Response(                          # ← retour avec Content-Type explicite
            json.dumps({
                'chemin_actuel': chemin,
                'parent':        str(os.path.dirname(chemin)),
                'contenu':       contenu,
                'raccourcis':    raccourcis
            }),
            content_type='application/json'       # ← ajout important
        )

    except PermissionError:
        return Response(
            json.dumps({'erreur': 'Permission refusée'}),
            status=403, content_type='application/json'
        )
    except FileNotFoundError:
        return Response(
            json.dumps({'erreur': 'Dossier introuvable'}),
            status=404, content_type='application/json'
        )

@files_bp.route('/apercu-organisation', methods=['POST'])
def apercu_organisation():
    """Retourne un aperçu des fichiers qui seront déplacés"""
    dossier = request.form.get('dossier_org', '').strip()

    if not os.path.isdir(dossier):
        return json.dumps({'erreur': 'Dossier introuvable'}), 404

    regles = {
        'Images':    ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
        'Documents': ['.pdf', '.doc', '.docx', '.odt', '.txt', '.md'],
        'Tableurs':  ['.xls', '.xlsx', '.csv', '.ods'],
        'Slides':    ['.ppt', '.pptx', '.odp'],
        'Archives':  ['.zip', '.tar', '.gz', '.rar', '.7z'],
        'Code':      ['.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.sh'],
        'Videos':    ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
        'Audio':     ['.mp3', '.wav', '.flac', '.aac'],
        'Autres':    []
    }

    apercu = {}
    fichiers = [
        f for f in os.listdir(dossier)
        if os.path.isfile(os.path.join(dossier, f))
        and not f.startswith('.')
    ]

    for fichier in fichiers:
        ext = os.path.splitext(fichier)[1].lower()
        categorie = 'Autres'
        for cat, extensions in regles.items():
            if ext in extensions:
                categorie = cat
                break

        if categorie not in apercu:
            apercu[categorie] = []
        apercu[categorie].append({
            'nom': fichier,
            'ext': ext or 'sans extension'
        })

    return Response(
        json.dumps({
            'apercu':       apercu,
            'total':        len(fichiers),
            'nb_categories': len(apercu)
        }),
        content_type='application/json'
    )