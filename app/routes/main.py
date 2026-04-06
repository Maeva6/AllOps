from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app.services.file_service import rename_files, image_to_pdf, merge_pdfs, organize_files
from app.models import FileOperation
from app.extensions import db
import os
import tempfile
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__, url_prefix='/')

@main_bp.route('/')
def index():
    return render_template('base.html', title="AllOps - Accueil")

files_bp = Blueprint('files', __name__, url_prefix='/files')

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Page principale du module ────────────────────────────────────────────────
@files_bp.route('/')
def index():
    # Récupère les 10 dernières opérations
    operations = FileOperation.query.order_by(
        FileOperation.created_at.desc()
    ).limit(10).all()
    return render_template('modules/files.html',
                           title="Module Fichiers",
                           operations=operations)


# ─── Renommage ────────────────────────────────────────────────────────────────
@files_bp.route('/rename', methods=['POST'])
def rename():
    folder_path = request.form.get('folder_path', '').strip()
    ancien      = request.form.get('ancien', '').strip()
    nouveau     = request.form.get('nouveau', '').strip()
    prefix      = request.form.get('prefix', '').strip()
    suffix      = request.form.get('suffix', '').strip()
    add_date    = request.form.get('add_date') == 'on'

    if not folder_path:
        flash("Veuillez entrer un chemin de dossier.", "danger")
        return redirect(url_for('files.index'))

    pattern = {"ancien": ancien, "nouveau": nouveau}
    result  = rename_files(folder_path, pattern, prefix, suffix, add_date)

    # Enregistre l'opération en base
    op = FileOperation(
        type_op     = "rename",
        nb_fichiers = result.get("total", 0),
        details     = f"Dossier: {folder_path} | {ancien} → {nouveau}",
        statut      = "success" if result["success"] else "error"
    )
    db.session.add(op)
    db.session.commit()

    flash(result["message"], "success" if result["success"] else "danger")
    return render_template('modules/files.html',
                           title="Module Fichiers",
                           result=result,
                           operations=FileOperation.query.order_by(
                               FileOperation.created_at.desc()).limit(10).all())


# ─── Fusion PDF ───────────────────────────────────────────────────────────────
@files_bp.route('/merge-pdf', methods=['POST'])
def merge_pdf():
    files = request.files.getlist('pdfs')

    if len(files) < 2:
        flash("Sélectionne au moins 2 fichiers PDF.", "danger")
        return redirect(url_for('files.index'))

    # Sauvegarde les fichiers uploadés en temp
    tmp_dir   = Path(tempfile.mkdtemp())
    pdf_paths = []

    for f in files:
        if f and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            path     = tmp_dir / filename
            f.save(path)
            pdf_paths.append(str(path))

    output_path = tmp_dir / "merged_output.pdf"
    result      = merge_pdfs(pdf_paths, str(output_path))

    op = FileOperation(
        type_op     = "merge_pdf",
        nb_fichiers = len(pdf_paths),
        details     = f"Fusion de {len(pdf_paths)} PDFs",
        statut      = "success" if result["success"] else "error"
    )
    db.session.add(op)
    db.session.commit()

    flash(result["message"], "success" if result["success"] else "danger")
    return redirect(url_for('files.index'))


# ─── Organisation ─────────────────────────────────────────────────────────────
@files_bp.route('/organize', methods=['POST'])
def organize():
    folder_path = request.form.get('folder_path', '').strip()

    if not folder_path:
        flash("Veuillez entrer un chemin de dossier.", "danger")
        return redirect(url_for('files.index'))

    result = organize_files(folder_path)

    op = FileOperation(
        type_op     = "organize",
        nb_fichiers = result.get("total", 0),
        details     = f"Dossier: {folder_path}",
        statut      = "success" if result["success"] else "error"
    )
    db.session.add(op)
    db.session.commit()

    flash(result["message"], "success" if result["success"] else "danger")
    return render_template('modules/files.html',
                           title="Module Fichiers",
                           result=result,
                           operations=FileOperation.query.order_by(
                               FileOperation.created_at.desc()).limit(10).all())