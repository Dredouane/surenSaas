"""
Prompts systèmes pour les Lentilles AO (Appels d'Offres).

Ce module contient tous les prompts utilisés par le moteur de Lentilles
pour l'analyse des candidatures, la comparaison de pricing et 
la rédaction assistée du mémoire technique.
"""

from typing import Dict, Any, Optional


class AOLensPrompts:
    """Collection de prompts pour les Lentilles d'analyse AO."""
    
    # ===================================================================
    # LENTILLE PRICING
    # ===================================================================
    
    PRICING_SYSTEM_PROMPT = """Tu es un expert en chiffrage et contrôle de gestion pour le BTP.
Ta mission est d'analyser un BPU candidature et de le comparer à l'historique de l'entreprise.

RÈGLES D'ANALYSE:
1. Identifie les postes où le prix candidature est >20% supérieur à la moyenne historique
2. Détecte les postes mal dimensionnés (quantités anormales)
3. Identifie les opportunités (postes où nous sommes compétitifs)
4. Fournis des recommandations concrètes d'ajustement

FACTEURS À CONSIDÉRER:
- Contexte géographique du projet
- Complexité technique
- Délai d'exécution
- Concurrence attendue
- Spécificités du CCTP

Ton doit être factuel, professionnel et chiffré."""

    @staticmethod
    def pricing_user_prompt(
        postes_candidature: list,
        historique_gagnant: list,
        contexte_projet: Dict[str, Any]
    ) -> str:
        """Construit le prompt utilisateur pour l'analyse pricing."""
        return f"""Analyse ce BPU candidature et compare-le à notre historique de victoires.

CONTEXTE DU PROJET:
- Nom: {contexte_projet.get('nom_projet', 'N/A')}
- Client: {contexte_projet.get('client_nom', 'N/A')}
- Montant total candidature: {contexte_projet.get('montant_total', 'N/A')} €

BPU CANDIDATURE ({len(postes_candidature)} postes):
{postes_candidature[:30]}  # Limiter à 30 postes principaux

HISTORIQUE POSTES SIMILAIRES (gagnés):
{historique_gagnant[:20]}  # Limiter à 20 références

TÂCHES:
1. Compare chaque poste majeur avec l'historique
2. Identifie les écarts >20%
3. Détecte les anomalies de quantité
4. Suggère des ajustements justifiés

FORMAT DE SORTIE (JSON):
{{
  "anomalies": [
    {{
      "poste_numero": "01.01.001",
      "poste_description": "...",
      "notre_prix": 850.00,
      "prix_marche_estime": 720.00,
      "ecart_pct": 18.1,
      "impact_total": 15000.00,
      "recommandation": "Réduire de 15% en optimisant...",
      "confiance": 0.85
    }}
  ],
  "opportunites": [
    {{
      "poste_numero": "...",
      "description": "...",
      "raison": "Nous avons un avantage compétitif sur..."
    }}
  ],
  "risques_quantite": [
    {{
      "poste_numero": "...",
      "quantite_candidature": 1000,
      "quantite_estimee": 800,
      "difference_pct": 25,
      "commentaire": "Quantité surestimée vs historique"
    }}
  ],
  "synthese": {{
    "nb_postes_analyses": 30,
    "nb_anomalies_detectees": 5,
    "montant_total_anomalies": 75000.00,
    "risque_global": "moyen",
    "recommandation_strategique": "..."
  }}
}}"""

    # ===================================================================
    # LENTILLE RÉDACTION
    # ===================================================================
    
    REDACTION_SYSTEM_PROMPT = """Tu es un rédacteur professionnel de mémoires techniques pour le BTP.
Tu rédiges des chapitres de mémoire technique pour répondre à des appels d'offres.

RÈGLES DE RÉDACTION:
1. Répondre POINT PAR POINT aux exigences du RC
2. Utiliser un ton professionnel, factuel et percutant
3. Argumenter avec des preuves concrètes (chiffres, références)
4. S'appuyer sur les arguments gagnants de l'historique
5. Adapter au contexte spécifique du projet
6. Structure claire avec titres et sous-parties

FORMAT:
- Titres en majuscules
- Paragraphes courts (3-5 phrases)
- Listes à puces pour les points clés
- Phrases d'impact en gras"""

    @staticmethod
    def redaction_user_prompt(
        chapitre: str,
        exigences_rc: list,
        references_gagnantes: list,
        contexte_projet: Dict[str, Any]
    ) -> str:
        """Construit le prompt utilisateur pour la rédaction."""
        return f"""Rédige le chapitre "{chapitre}" du mémoire technique.

CONTEXTE DU PROJET:
- Nom: {contexte_projet.get('nom_projet', 'N/A')}
- Client: {contexte_projet.get('client_nom', 'N/A')}
- Description: {contexte_projet.get('description', 'N/A')}
- Montant: {contexte_projet.get('montant_total', 'N/A')} €
- Durée: {contexte_projet.get('duree_travaux_jours', 'N/A')} jours

EXIGENCES DU RC POUR CE CHAPITRE:
{chr(10).join(f'- {e}' for e in exigences_rc[:10])}

ARGUMENTS GAGNANTS (dossiers similaires remportés):
{references_gagnantes[:5]}

INSTRUCTIONS:
1. Rédige un chapitre complet (minimum 500 mots)
2. Réponds à toutes les exigences du RC
3. Intègre les arguments gagnants adaptés au contexte
4. Utilise des exemples concrets
5. Termine par un paragraphe de synthèse

Format: Texte structuré avec HTML simple (<h3>, <p>, <ul>, <li>, <strong>)"""

    # ===================================================================
    # LENTILLE RISQUE
    # ===================================================================
    
    RISQUE_SYSTEM_PROMPT = """Tu es un expert en analyse des risques contractuels pour le BTP.
Tu analyses les RC et CCTP pour identifier les risques majeurs.

RÈGLES D'ANALYSE:
1. Identifier les clauses pénalisantes (retards, non-conformité)
2. Détecter les obligations contractuelles lourdes
3. Évaluer les risques techniques mentionnés
4. Analyser les conditions de paiement
5. Identifier les points de vigilance juridique

Tonalité factuelle, alertes claires avec niveau de criticité."""

    @staticmethod
    def risque_user_prompt(
        contenu_rc: str,
        contenu_cctp: Optional[str] = None
    ) -> str:
        """Construit le prompt utilisateur pour l'analyse des risques."""
        cctp_section = f"""
CONTENU CCTP:
{contenu_cctp[:5000] if contenu_cctp else 'Non fourni'}
""" if contenu_cctp else ""
        
        return f"""Analyse ce RC pour identifier les risques contractuels majeurs.

CONTENU RC:
{contenu_rc[:8000]}
{cctp_section}

FORMAT DE SORTIE (JSON):
{{
  "score_global": 65,
  "niveau_risque": "moyen",
  "risques_identifies": [
    {{
      "categorie": "contractuel",
      "niveau": "élevé",
      "description": "Pénalités de retard de 1% par semaine",
      "impact_potentiel": "10% du montant du marché",
      "recommandation": "Négocier plafonnement à 5%"
    }}
  ],
  "clauses_dangereuses": [
    {{
      "clause": "Article 12.3",
      "texte": "...",
      "risque": "Obligation de résultat trop large"
    }}
  ],
  "points_de_vigilance": [
    "Délai très court vs complexité",
    "Exigences techniques inhabituelles"
  ],
  "recommandations": [
    "Demander clarification sur article X",
    "Prévoir marge sécurité 15%"
  ]
}}"""

    # ===================================================================
    # LENTILLE COMPARAISON (Gagné vs Perdu)
    # ===================================================================
    
    COMPARAISON_SYSTEM_PROMPT = """Tu es un analyste en stratégie commerciale BTP.
Tu compares des candidatures gagnées et perdues pour identifier les facteurs clés de succès.

RÈGLES:
1. Identifier les écarts de pricing significatifs
2. Comparer les arguments techniques
3. Analyser les points forts des gagnants
4. Identifier les erreurs des perdants
5. Recommander des ajustements"""

    @staticmethod
    def comparaison_user_prompt(
        candidature_actuelle: Dict[str, Any],
        gagnes_similaires: list,
        perdus_similaires: list
    ) -> str:
        """Construit le prompt utilisateur pour la comparaison."""
        return f"""Compare cette candidature avec nos historiques gagnés et perdus similaires.

CANDIDATURE ACTUELLE:
- Projet: {candidature_actuelle.get('nom_projet')}
- Montant: {candidature_actuelle.get('montant_total')} €
- Statut: {candidature_actuelle.get('statut')}

HISTORIQUE GAGNÉ ({len(gagnes_similaires)} projets):
{gagnes_similaires[:5]}

HISTORIQUE PERDU ({len(perdus_similaires)} projets):
{perdus_similaires[:5]}

FORMAT DE SORTIE (JSON):
{{
  "positionnement_prix": {{
    "vs_gagnes": "+5%",
    "vs_perdus": "-8%",
    "recommandation": "Léger ajustement possible"
  }},
  "facteurs_succes_identifies": [
    "Argumentaire technique détaillé",
    "Références similaires solides"
  ],
  "points_amelioration": [
    "Renforcer le chapitre sécurité"
  ],
  "probabilite_gain": 0.72,
  "recommandations_strategiques": [
    "Mettre en avant la référence X",
    "Ajouter un plan qualité renforcé"
  ]
}}"""

    # ===================================================================
    # LENTILLE OPPORTUNITÉ
    # ===================================================================
    
    OPPORTUNITE_SYSTEM_PROMPT = """Tu es un chasseur d'affaires BTP.
Tu analyses les AO pour identifier les opportunités et menaces.

RÈGLES:
1. Évaluer la qualité du client
2. Analyser la concurrence probable
3. Identifier les leviers différenciants
4. Évaluer le potentiel de marge
5. Recommander GO/NO-GO"""

    @staticmethod
    def opportunite_user_prompt(
        contexte_ao: Dict[str, Any],
        historique_client: Optional[list] = None
    ) -> str:
        """Construit le prompt utilisateur pour l'analyse d'opportunité."""
        # Construire la section historique séparément pour éviter les f-strings imbriquées
        if historique_client:
            historique_str = "\n".join(f"- {h}" for h in historique_client[:3])
        else:
            historique_str = "Pas d'historique avec ce client"
        
        return f"""Analyse cette opportunité d'affaire.

CONTEXTE AO:
- Client: {contexte_ao.get('client_nom')}
- Projet: {contexte_ao.get('nom_projet')}
- Montant estimé: {contexte_ao.get('montant_total')} €
- Délai: {contexte_ao.get('duree_travaux_jours')} jours
- Date limite: {contexte_ao.get('date_limite_remise')}

{historique_str}

FORMAT DE SORTIE (JSON):
{{
  "attractivite": {{
    "score": 75,
    "niveau": "bonne",
    "justification": "..."
  }},
  "forces": [
    "Client fidèle",
    "Projet dans notre cœur de métier"
  ],
  "faiblesses": [
    "Délai court",
    "Concurrence attendue forte"
  ],
  "leviers_différenciants": [
    "Nos références similaires",
    "Proximité géographique"
  ],
  "recommandation": "GO",
  "actions_requises": [
    "Contacter le client",
    "Constituer l'équipe projet"
  ]
}}"""

    # ===================================================================
    # PETIT PROMPT (Itération Draft)
    # ===================================================================
    
    PETIT_PROMPT_SYSTEM = """Tu es un assistant de rédaction. Tu modifies un texte selon l'instruction donnée.
Règles:
- Préserver le sens et les faits
- Maintenir le ton professionnel
- Ne pas inventer d'informations
- Répondre de manière concise"""

    @staticmethod
    def petit_prompt_user(current_content: str, instruction: str) -> str:
        """Construit le prompt pour l'itération sur un draft."""
        return f"""Modifie ce texte selon l'instruction.

TEXTE ACTUEL:
{current_content}

INSTRUCTION:
{instruction}

Réponds uniquement avec le texte modifié, sans commentaire additionnel."""


# Instance pour import facile
ao_lens_prompts = AOLensPrompts()
