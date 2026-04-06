import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF


# ─── Renommage en masse ───────────────────────────────────────────────────────
def rename_files(folder_path, pattern, prefix="", suffix="", add_date=False):
    """
    Renomme tous les fichiers d'un dossier selon un pattern.
    pattern  : texte à remplacer dans le nom (ex: "TP" → "Travail_Pratique")
    prefix   : texte à ajouter au début du nom
    suffix   : texte à ajouter à la fin (avant l'extension)
    add_date : ajoute la date du jour au nom
    """
    results = []
    folder = Path(folder_path)

    if not folder.exists():
        return {"success": False, "message": "Dossier introuvable", "files": []}

    for file in folder.iterdir():
        if not file.is_file():
            continue

        stem      = file.stem        # nom sans extension
        extension = file.suffix      # .pdf, .docx...

        new_stem = stem

        # Appliquer le pattern de remplacement
        if pattern.get("ancien") and pattern.get("nouveau"):
            new_stem = new_stem.replace(pattern["ancien"], pattern["nouveau"])

        # Ajouter préfixe
        if prefix:
            new_stem = prefix + "_" + new_stem

        # Ajouter suffixe
        if suffix:
            new_stem = new_stem + "_" + suffix

        # Ajouter la date
        if add_date:
            date_str = datetime.now().strftime("%Y-%m-%d")
            new_stem = new_stem + "_" + date_str

        new_name = new_stem + extension
        new_path = folder / new_name

        try:
            file.rename(new_path)
            results.append({
                "ancien": file.name,
                "nouveau": new_name,
                "statut": "success"
            })
        except Exception as e:
            results.append({
                "ancien": file.name,
                "nouveau": new_name,
                "statut": "error",
                "erreur": str(e)
            })

    return {
        "success": True,
        "total": len(results),
        "message": f"{len(results)} fichier(s) renommé(s)",
        "files": results
    }


# ─── Conversion en PDF ────────────────────────────────────────────────────────
def image_to_pdf(image_paths, output_path):
    """Convertit une ou plusieurs images en un seul PDF."""
    images = []

    for img_path in image_paths:
        img = Image.open(img_path).convert("RGB")
        images.append(img)

    if not images:
        return {"success": False, "message": "Aucune image fournie"}

    first   = images[0]
    rest    = images[1:]

    first.save(output_path, save_all=True, append_images=rest, format="PDF")

    return {
        "success": True,
        "message": f"{len(images)} image(s) converties en PDF",
        "output": str(output_path)
    }


def merge_pdfs(pdf_paths, output_path):
    """Fusionne plusieurs PDFs en un seul."""
    merged = fitz.open()

    for pdf_path in pdf_paths:
        with fitz.open(pdf_path) as doc:
            merged.insert_pdf(doc)

    merged.save(output_path)
    merged.close()

    return {
        "success": True,
        "message": f"{len(pdf_paths)} PDF(s) fusionné(s)",
        "output": str(output_path)
    }


# ─── Organisation automatique ─────────────────────────────────────────────────
CATEGORIES = {
    "PDF":       [".pdf"],
    "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "Documents": [".docx", ".doc", ".odt", ".txt", ".md"],
    "Tableaux":  [".xlsx", ".xls", ".csv"],
    "Code":      [".py", ".js", ".html", ".css", ".json", ".yml", ".yaml"],
    "Archives":  [".zip", ".tar", ".gz", ".rar"],
}

def organize_files(folder_path):
    """
    Scanne un dossier et range les fichiers dans des sous-dossiers
    selon leur type (PDF, Images, Documents, etc.)
    """
    results = []
    folder  = Path(folder_path)

    if not folder.exists():
        return {"success": False, "message": "Dossier introuvable", "files": []}

    for file in folder.iterdir():
        if not file.is_file():
            continue

        ext      = file.suffix.lower()
        category = "Autres"

        for cat, extensions in CATEGORIES.items():
            if ext in extensions:
                category = cat
                break

        dest_folder = folder / category
        dest_folder.mkdir(exist_ok=True)
        dest_path = dest_folder / file.name

        try:
            shutil.move(str(file), str(dest_path))
            results.append({
                "fichier":    file.name,
                "categorie":  category,
                "statut":     "success"
            })
        except Exception as e:
            results.append({
                "fichier":  file.name,
                "categorie": category,
                "statut":   "error",
                "erreur":   str(e)
            })

    return {
        "success": True,
        "total":   len(results),
        "message": f"{len(results)} fichier(s) organisé(s)",
        "files":   results
    }