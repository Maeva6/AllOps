# app/data/quiz_questions.py
# 80+ questions avec niveau de difficulté (1=facile, 2=moyen, 3=difficile)

QUESTIONS = [
  # ── LINUX ──────────────────────────────────────────────────────────────────
  { "q":"Quelle commande affiche le contenu d'un dossier ?",
    "choices":["ls","dir","show","list"], "correct":0,
    "domain":"Linux","diff":1 },
  { "q":"Comment afficher le manuel d'une commande Linux ?",
    "choices":["man <cmd>","help <cmd>","info <cmd>","doc <cmd>"],
    "correct":0,"domain":"Linux","diff":1 },
  { "q":"Quelle commande affiche l'utilisation disque ?",
    "choices":["df -h","du -sh","disk show","fdisk -l"],
    "correct":0,"domain":"Linux","diff":1 },
  { "q":"Que fait 'chmod 755 script.sh' ?",
    "choices":["rwxr-xr-x","rwxrwxrwx","r-xr-xr-x","rwx------"],
    "correct":0,"domain":"Linux","diff":2 },
  { "q":"Quelle commande trouve les fichiers .log modifiés il y a moins de 2 jours ?",
    "choices":["find / -name '*.log' -mtime -2","grep -r '*.log' /","locate *.log -d 2","ls -lt *.log"],
    "correct":0,"domain":"Linux","diff":3 },
  { "q":"Que signifie le signal SIGKILL (kill -9) ?",
    "choices":["Arrêt immédiat non interceptable","Pause du processus","Redémarrage propre","Envoi d'un message"],
    "correct":0,"domain":"Linux","diff":3 },
  { "q":"Quelle commande compresse un dossier en tar.gz ?",
    "choices":["tar -czf archive.tar.gz dossier","zip -r dossier","gzip -r dossier","compress dossier"],
    "correct":0,"domain":"Linux","diff":2 },
  { "q":"Quelle commande affiche les 10 dernières lignes d'un fichier en temps réel ?",
    "choices":["tail -f fichier","head -f fichier","watch cat fichier","tail -n 10 fichier"],
    "correct":0,"domain":"Linux","diff":2 },

  # ── GIT ────────────────────────────────────────────────────────────────────
  { "q":"Quelle commande initialise un repository Git ?",
    "choices":["git init","git start","git new","git create"],
    "correct":0,"domain":"Git","diff":1 },
  { "q":"Comment créer et basculer sur une nouvelle branche ?",
    "choices":["git checkout -b <branche>","git branch -new <branche>","git switch --create <branche>","Les deux A et C sont correctes"],
    "correct":3,"domain":"Git","diff":2 },
  { "q":"Que fait 'git stash' ?",
    "choices":["Sauvegarde temporairement les modifications","Supprime les modifications","Crée un commit","Fusionne les branches"],
    "correct":0,"domain":"Git","diff":2 },
  { "q":"Quelle commande annule le dernier commit en gardant les modifications ?",
    "choices":["git reset HEAD~1","git revert HEAD","git undo","git rollback"],
    "correct":0,"domain":"Git","diff":2 },
  { "q":"Quelle est la différence entre git merge et git rebase ?",
    "choices":["merge crée un commit de fusion, rebase réécrit l'historique","Ils sont identiques","merge est plus rapide","rebase crée un commit de fusion"],
    "correct":0,"domain":"Git","diff":3 },
  { "q":"Que fait 'git cherry-pick <hash>' ?",
    "choices":["Applique un commit spécifique sur la branche courante","Sélectionne une branche","Copie un repository","Supprime un commit"],
    "correct":0,"domain":"Git","diff":3 },
  { "q":"Quelle commande affiche l'historique des commits de façon graphique ?",
    "choices":["git log --oneline --graph","git history","git show --graph","git branch --log"],
    "correct":0,"domain":"Git","diff":2 },

  # ── DOCKER ─────────────────────────────────────────────────────────────────
  { "q":"Quelle commande liste les conteneurs en cours d'exécution ?",
    "choices":["docker ps","docker ls","docker list","docker show"],
    "correct":0,"domain":"Docker","diff":1 },
  { "q":"Comment construire une image depuis un Dockerfile ?",
    "choices":["docker build -t nom .","docker create -t nom .","docker compile -t nom .","docker make nom"],
    "correct":0,"domain":"Docker","diff":1 },
  { "q":"Quelle instruction Dockerfile définit l'image de base ?",
    "choices":["FROM","BASE","IMAGE","START"],
    "correct":0,"domain":"Docker","diff":1 },
  { "q":"Que fait 'docker-compose down' ?",
    "choices":["Arrête et supprime les conteneurs/réseaux","Arrête uniquement les conteneurs","Supprime les volumes","Redémarre les conteneurs"],
    "correct":0,"domain":"Docker","diff":2 },
  { "q":"Quelle est la différence entre COPY et ADD dans un Dockerfile ?",
    "choices":["ADD supporte les URLs et archives tar, COPY est simple","Ils sont identiques","COPY supporte les URLs","ADD est déprécié"],
    "correct":0,"domain":"Docker","diff":3 },
  { "q":"Que fait l'instruction ENTRYPOINT dans un Dockerfile ?",
    "choices":["Définit la commande principale du conteneur","Définit le dossier de travail","Expose un port","Définit une variable d'environnement"],
    "correct":0,"domain":"Docker","diff":2 },
  { "q":"Comment supprimer toutes les images Docker non utilisées ?",
    "choices":["docker image prune -a","docker rm --all","docker rmi *","docker clean images"],
    "correct":0,"domain":"Docker","diff":2 },
  { "q":"Que signifie '--network=host' dans docker run ?",
    "choices":["Le conteneur partage la pile réseau de l'hôte","Le conteneur est isolé","Le conteneur n'a pas de réseau","Crée un réseau nommé 'host'"],
    "correct":0,"domain":"Docker","diff":3 },

  # ── CI/CD ──────────────────────────────────────────────────────────────────
  { "q":"Que signifie CI dans CI/CD ?",
    "choices":["Continuous Integration","Code Inspection","Container Interface","Central Index"],
    "correct":0,"domain":"CI/CD","diff":1 },
  { "q":"Dans GitHub Actions, comment s'appelle un pipeline ?",
    "choices":["workflow","pipeline","action","trigger"],
    "correct":0,"domain":"CI/CD","diff":1 },
  { "q":"Quel fichier définit un workflow GitHub Actions ?",
    "choices":[".github/workflows/ci.yml","github-actions.yml","ci-pipeline.yml",".github/ci.yaml"],
    "correct":0,"domain":"CI/CD","diff":2 },
  { "q":"Que fait 'needs' dans un job GitHub Actions ?",
    "choices":["Définit une dépendance entre jobs","Installe des dépendances","Définit les secrets","Lance un autre workflow"],
    "correct":0,"domain":"CI/CD","diff":2 },
  { "q":"Quelle est la différence entre Continuous Delivery et Continuous Deployment ?",
    "choices":["Delivery nécessite approbation manuelle, Deployment est automatique","Ils sont identiques","Deployment nécessite approbation manuelle","Delivery est automatique"],
    "correct":0,"domain":"CI/CD","diff":3 },
  { "q":"Qu'est-ce qu'un artefact dans un pipeline CI/CD ?",
    "choices":["Un fichier produit par le pipeline (ex: binaire, image)","Un test échoué","Un secret","Une variable d'environnement"],
    "correct":0,"domain":"CI/CD","diff":2 },

  # ── CLOUD ──────────────────────────────────────────────────────────────────
  { "q":"Que signifie IaaS ?",
    "choices":["Infrastructure as a Service","Integration as a Service","Interface as a System","Index as a Service"],
    "correct":0,"domain":"Cloud","diff":1 },
  { "q":"Qu'est-ce qu'une région dans AWS ?",
    "choices":["Un emplacement géographique avec plusieurs data centers","Un pays unique","Un seul data center","Un type de service"],
    "correct":0,"domain":"Cloud","diff":2 },
  { "q":"Que fait AWS IAM ?",
    "choices":["Gère les identités et accès","Héberge des sites web","Stocke des fichiers","Lance des VMs"],
    "correct":0,"domain":"Cloud","diff":2 },
  { "q":"Quelle est la différence entre scale-up et scale-out ?",
    "choices":["Scale-up = plus de ressources par machine, Scale-out = plus de machines","Ils sont identiques","Scale-out = plus de ressources par machine","Scale-up = plus de machines"],
    "correct":0,"domain":"Cloud","diff":3 },

  # ── PYTHON ─────────────────────────────────────────────────────────────────
  { "q":"Quelle est la sortie de : print(type([])).__name__ ?",
    "choices":["list","array","tuple","dict"],
    "correct":0,"domain":"Python","diff":1 },
  { "q":"Que fait le décorateur @staticmethod en Python ?",
    "choices":["Définit une méthode sans accès à self ni cls","Rend la méthode privée","Définit une propriété","Cache la méthode"],
    "correct":0,"domain":"Python","diff":2 },
  { "q":"Quelle est la complexité temporelle d'une recherche dans un dict Python ?",
    "choices":["O(1) en moyenne","O(n)","O(log n)","O(n²)"],
    "correct":0,"domain":"Python","diff":3 },
  { "q":"Que fait 'yield' en Python ?",
    "choices":["Crée un générateur","Retourne une valeur et termine la fonction","Lève une exception","Passe à l'itération suivante"],
    "correct":0,"domain":"Python","diff":2 },
  { "q":"Quelle est la différence entre '==' et 'is' en Python ?",
    "choices":["== compare les valeurs, is compare les identités (adresses mémoire)","Ils sont identiques","is compare les valeurs","== compare les identités"],
    "correct":0,"domain":"Python","diff":2 },

  # ── SÉCURITÉ ───────────────────────────────────────────────────────────────
  { "q":"Que signifie HTTPS par rapport à HTTP ?",
    "choices":["HTTPS chiffre les données avec TLS/SSL","HTTPS est plus rapide","HTTPS utilise un port différent uniquement","HTTPS est une version plus récente"],
    "correct":0,"domain":"Sécurité","diff":1 },
  { "q":"Qu'est-ce qu'une injection SQL ?",
    "choices":["Insertion de code SQL malveillant dans une requête","Une technique de sauvegarde","Un type de chiffrement","Un protocole réseau"],
    "correct":0,"domain":"Sécurité","diff":2 },
  { "q":"Que fait un pare-feu applicatif (WAF) ?",
    "choices":["Filtre le trafic HTTP/HTTPS malveillant","Chiffre les données","Gère les certificats SSL","Bloque le spam email"],
    "correct":0,"domain":"Sécurité","diff":2 },

  # ── RÉSEAU ─────────────────────────────────────────────────────────────────
  { "q":"Sur quel port écoute HTTP par défaut ?",
    "choices":["80","443","8080","3000"],
    "correct":0,"domain":"Réseau","diff":1 },
  { "q":"Que fait la commande 'ping' ?",
    "choices":["Teste la connectivité réseau avec une adresse","Affiche les routes","Configure une interface réseau","Résout un nom de domaine"],
    "correct":0,"domain":"Réseau","diff":1 },
  { "q":"Quelle est la plage d'adresses IP privées de classe C ?",
    "choices":["192.168.0.0/16","10.0.0.0/8","172.16.0.0/12","169.254.0.0/16"],
    "correct":0,"domain":"Réseau","diff":2 },
  { "q":"Que signifie BGP dans le contexte des réseaux ?",
    "choices":["Border Gateway Protocol — protocole de routage inter-AS","Basic Gateway Protocol","Binary Group Protocol","Bridged Gateway Path"],
    "correct":0,"domain":"Réseau","diff":3 },

  # ── KUBERNETES ─────────────────────────────────────────────────────────────
  { "q":"Quelle est l'unité de déploiement minimale dans Kubernetes ?",
    "choices":["Pod","Container","Node","Cluster"],
    "correct":0,"domain":"Kubernetes","diff":1 },
  { "q":"Que fait un Service dans Kubernetes ?",
    "choices":["Expose des pods sur le réseau de manière stable","Stocke la configuration","Gère les volumes","Définit les ressources CPU"],
    "correct":0,"domain":"Kubernetes","diff":2 },
  { "q":"Quelle est la différence entre un Deployment et un StatefulSet ?",
    "choices":["StatefulSet maintient une identité stable pour chaque pod","Deployment est plus récent","StatefulSet est pour les apps stateless","Ils sont identiques"],
    "correct":0,"domain":"Kubernetes","diff":3 },
]

def get_questions_for_level(level: int) -> list:
    """
    Sélectionne et retourne les questions adaptées au niveau.
    Algorithme de pondération selon la difficulté.
    """
    import random

    # Config par niveau
    configs = [
        # (nb_questions, poids_diff1, poids_diff2, poids_diff3)
        (5,  0.8, 0.2, 0.0),  # N1
        (5,  0.7, 0.3, 0.0),  # N2
        (5,  0.5, 0.5, 0.0),  # N3
        (8,  0.4, 0.5, 0.1),  # N4
        (8,  0.3, 0.5, 0.2),  # N5
        (8,  0.2, 0.5, 0.3),  # N6
        (10, 0.1, 0.6, 0.3),  # N7
        (10, 0.1, 0.5, 0.4),  # N8
        (10, 0.0, 0.5, 0.5),  # N9
        (12, 0.0, 0.4, 0.6),  # N10
        (15, 0.0, 0.3, 0.7),  # N11
        (15, 0.0, 0.2, 0.8),  # N12
        (20, 0.0, 0.1, 0.9),  # N13
        (20, 0.0, 0.0, 1.0),  # N14
        (25, 0.0, 0.0, 1.0),  # N15
    ]

    nb, w1, w2, w3 = configs[level - 1]

    # Séparer par difficulté
    easy   = [q for q in QUESTIONS if q['diff'] == 1]
    medium = [q for q in QUESTIONS if q['diff'] == 2]
    hard   = [q for q in QUESTIONS if q['diff'] == 3]

    # Calculer combien de questions de chaque difficulté
    n1 = round(nb * w1)
    n2 = round(nb * w2)
    n3 = nb - n1 - n2

    # Sélection aléatoire sans répétition
    selected = (
        random.sample(easy,   min(n1, len(easy)))   +
        random.sample(medium, min(n2, len(medium))) +
        random.sample(hard,   min(n3, len(hard)))
    )

    # Compléter si manque de questions d'une catégorie
    remaining = nb - len(selected)
    if remaining > 0:
        pool = [q for q in QUESTIONS if q not in selected]
        selected += random.sample(pool, min(remaining, len(pool)))

    # Mélanger les réponses de chaque question et l'ordre des questions
    result = []
    for q in random.sample(selected, len(selected)):
        choices     = list(enumerate(q['choices']))
        correct_txt = q['choices'][q['correct']]
        random.shuffle(choices)
        new_correct = next(i for i, (_, txt) in enumerate(choices) if txt == correct_txt)
        result.append({
            **q,
            'choices': [txt for _, txt in choices],
            'correct': new_correct
        })

    return result