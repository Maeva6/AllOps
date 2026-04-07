# app/data/ressources_suggestions.py
# Ressources suggérées automatiquement par certification

SUGGESTIONS = {
    # ── AWS ──────────────────────────────────────────────────────────────────
    "aws cloud practitioner": [
        {
            "titre":   "AWS Skill Builder – Cloud Practitioner",
            "url":     "https://explore.skillbuilder.aws/learn",
            "type":    "cours",
            "gratuit": True
        },
        {
            "titre":   "Cours AWS CCP – FreeCodeCamp (YouTube)",
            "url":     "https://www.youtube.com/watch?v=NhDYbskXRgc",
            "type":    "video",
            "gratuit": True
        },
        {
            "titre":   "AWS Documentation officielle",
            "url":     "https://docs.aws.amazon.com",
            "type":    "doc",
            "gratuit": True
        },
    ],
    "aws solutions architect": [
        {
            "titre":   "AWS Solutions Architect – Stephane Maarek (Udemy)",
            "url":     "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03",
            "type":    "cours",
            "gratuit": False
        },
        {
            "titre":   "AWS SAA – TechWorld with Nana (YouTube)",
            "url":     "https://www.youtube.com/watch?v=BRuvq59miIo",
            "type":    "video",
            "gratuit": True
        },
    ],

    # ── Docker ────────────────────────────────────────────────────────────────
    "docker": [
        {
            "titre":   "Play with Docker – Labs interactifs",
            "url":     "https://labs.play-with-docker.com",
            "type":    "pratique",
            "gratuit": True
        },
        {
            "titre":   "Docker pour débutants – TechWorld with Nana (YouTube)",
            "url":     "https://www.youtube.com/watch?v=3c-iBn73dDE",
            "type":    "video",
            "gratuit": True
        },
        {
            "titre":   "Documentation officielle Docker",
            "url":     "https://docs.docker.com/get-started",
            "type":    "doc",
            "gratuit": True
        },
        {
            "titre":   "KodeKloud – Docker for Beginners",
            "url":     "https://kodekloud.com/courses/docker-for-the-absolute-beginner",
            "type":    "cours",
            "gratuit": True
        },
    ],

    # ── Linux ─────────────────────────────────────────────────────────────────
    "linux": [
        {
            "titre":   "Linux Foundation LFS101 – Introduction to Linux",
            "url":     "https://training.linuxfoundation.org/training/introduction-to-linux",
            "type":    "cours",
            "gratuit": True
        },
        {
            "titre":   "The Linux Command Line (livre gratuit en ligne)",
            "url":     "https://linuxcommand.org/tlcl.php",
            "type":    "livre",
            "gratuit": True
        },
        {
            "titre":   "Linux pour débutants – NetworkChuck (YouTube)",
            "url":     "https://www.youtube.com/watch?v=ZtqBQ68cfJc",
            "type":    "video",
            "gratuit": True
        },
    ],
    "lfcs": [
        {
            "titre":   "LFCS – Linux Foundation",
            "url":     "https://training.linuxfoundation.org/certification/linux-foundation-certified-sysadmin-lfcs",
            "type":    "cours",
            "gratuit": False
        },
        {
            "titre":   "KodeKloud – Linux Fundamentals",
            "url":     "https://kodekloud.com/courses/linux-basics",
            "type":    "cours",
            "gratuit": True
        },
    ],

    # ── Kubernetes ────────────────────────────────────────────────────────────
    "kubernetes": [
        {
            "titre":   "Play with Kubernetes – Labs interactifs",
            "url":     "https://labs.play-with-k8s.com",
            "type":    "pratique",
            "gratuit": True
        },
        {
            "titre":   "Kubernetes – TechWorld with Nana (YouTube)",
            "url":     "https://www.youtube.com/watch?v=X48VuDVv0do",
            "type":    "video",
            "gratuit": True
        },
        {
            "titre":   "Documentation officielle Kubernetes",
            "url":     "https://kubernetes.io/docs/home",
            "type":    "doc",
            "gratuit": True
        },
    ],
    "kcna": [
        {
            "titre":   "KCNA – Linux Foundation",
            "url":     "https://training.linuxfoundation.org/certification/kubernetes-cloud-native-associate",
            "type":    "cours",
            "gratuit": False
        },
    ],

    # ── Terraform ─────────────────────────────────────────────────────────────
    "terraform": [
        {
            "titre":   "Tutoriels Terraform – HashiCorp",
            "url":     "https://developer.hashicorp.com/terraform/tutorials",
            "type":    "pratique",
            "gratuit": True
        },
        {
            "titre":   "Terraform – TechWorld with Nana (YouTube)",
            "url":     "https://www.youtube.com/watch?v=l5k1ai_GBDE",
            "type":    "video",
            "gratuit": True
        },
    ],

    # ── GitHub ────────────────────────────────────────────────────────────────
    "github": [
        {
            "titre":   "GitHub Skills – Parcours interactifs",
            "url":     "https://skills.github.com",
            "type":    "pratique",
            "gratuit": True
        },
        {
            "titre":   "GitHub Actions – Documentation officielle",
            "url":     "https://docs.github.com/actions",
            "type":    "doc",
            "gratuit": True
        },
    ],

    # ── Python ────────────────────────────────────────────────────────────────
    "python": [
        {
            "titre":   "Python Institute – PCEP préparation",
            "url":     "https://pythoninstitute.org/pcep",
            "type":    "cours",
            "gratuit": False
        },
        {
            "titre":   "Python pour débutants – FreeCodeCamp (YouTube)",
            "url":     "https://www.youtube.com/watch?v=eWRyvpFB_1M",
            "type":    "video",
            "gratuit": True
        },
        {
            "titre":   "Documentation officielle Python",
            "url":     "https://docs.python.org/3",
            "type":    "doc",
            "gratuit": True
        },
    ],

    # ── Cisco / Réseaux ───────────────────────────────────────────────────────
    "cisco": [
        {
            "titre":   "Cisco NetAcad – Introduction to Networks",
            "url":     "https://www.netacad.com/courses/networking/ccna-introduction-networks",
            "type":    "cours",
            "gratuit": True
        },
        {
            "titre":   "CCNA – NetworkChuck (YouTube)",
            "url":     "https://www.youtube.com/watch?v=rv3QK2UquxM",
            "type":    "video",
            "gratuit": True
        },
    ],
    "ccna": [
        {
            "titre":   "Cisco NetAcad – CCNA",
            "url":     "https://www.netacad.com",
            "type":    "cours",
            "gratuit": True
        },
        {
            "titre":   "Packet Tracer – Simulateur réseau gratuit",
            "url":     "https://www.netacad.com/courses/packet-tracer",
            "type":    "pratique",
            "gratuit": True
        },
    ],

    # ── Sécurité ──────────────────────────────────────────────────────────────
    "securite": [
        {
            "titre":   "OWASP – Top 10 des vulnérabilités",
            "url":     "https://owasp.org/www-project-top-ten",
            "type":    "doc",
            "gratuit": True
        },
        {
            "titre":   "OWASP DevSecOps Guideline",
            "url":     "https://owasp.org/www-project-devsecops-guideline",
            "type":    "doc",
            "gratuit": True
        },
    ],

    # ── Anglais / TOEIC ───────────────────────────────────────────────────────
    "toeic": [
        {
            "titre":   "BBC Learning English",
            "url":     "https://www.bbc.co.uk/learningenglish",
            "type":    "cours",
            "gratuit": True
        },
        {
            "titre":   "Duolingo – Anglais",
            "url":     "https://www.duolingo.com",
            "type":    "pratique",
            "gratuit": True
        },
        {
            "titre":   "TOEIC – Préparation officielle ETS",
            "url":     "https://www.ets.org/toeic/test-takers/listening-reading/prepare.html",
            "type":    "cours",
            "gratuit": True
        },
    ],

    # ── Grafana / Prometheus ──────────────────────────────────────────────────
    "grafana": [
        {
            "titre":   "Grafana Fundamentals – Tutoriels officiels",
            "url":     "https://grafana.com/tutorials/grafana-fundamentals",
            "type":    "cours",
            "gratuit": True
        },
    ],
    "prometheus": [
        {
            "titre":   "Prometheus – Documentation officielle",
            "url":     "https://prometheus.io/docs/introduction/overview",
            "type":    "doc",
            "gratuit": True
        },
        {
            "titre":   "Prometheus & Grafana – TechWorld with Nana (YouTube)",
            "url":     "https://www.youtube.com/watch?v=h4Sl21AKiDg",
            "type":    "video",
            "gratuit": True
        },
    ],

    # ── Google Cloud ──────────────────────────────────────────────────────────
    "google cloud": [
        {
            "titre":   "Google Cloud Skills Boost",
            "url":     "https://cloudskillsboost.google",
            "type":    "pratique",
            "gratuit": True
        },
        {
            "titre":   "Google ACE – Documentation officielle",
            "url":     "https://cloud.google.com/certification/cloud-engineer",
            "type":    "doc",
            "gratuit": True
        },
    ],
}


def get_suggestions(nom_certification: str, organisme: str = "") -> list:
    """
    Retourne les suggestions de ressources pour une certification donnée.
    Cherche par mots-clés dans le nom et l'organisme.
    """
    nom_lower = nom_certification.lower()
    org_lower  = organisme.lower()
    resultats  = []
    deja_vus   = set()

    for cle, ressources in SUGGESTIONS.items():
        if cle in nom_lower or cle in org_lower:
            for r in ressources:
                if r['url'] not in deja_vus:
                    resultats.append(r)
                    deja_vus.add(r['url'])

    return resultats