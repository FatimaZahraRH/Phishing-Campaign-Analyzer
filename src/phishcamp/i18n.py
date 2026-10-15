"""Page « moment pédagogique » de chaque campagne, en français et en anglais.

L'offre type d'une équipe SecOps inclut la TRADUCTION des campagnes pour un
public international. On génère ici, à partir de la description de la
campagne, la page vue après un clic ou un signalement.

Principes (Ho et al. 2025 : la plupart des sessions de formation durent moins
d'une minute) : court, concret, centré sur les indices de CET e-mail, ton
bienveillant, et le geste à retenir : signaler.
"""
from __future__ import annotations

CUE_EN = {
    "faute d'orthographe dans l'objet": "spelling mistake in the subject line",
    "faute de grammaire dans le texte": "grammar mistake in the body",
    "formule de politesse inhabituelle": "unusual greeting or sign-off",
    "domaine d'expéditeur externe": "sender domain from outside the company",
    "lien vers un domaine inconnu": "link to an unknown domain",
    "adresse de réponse différente": "reply-to address differs from the sender",
    "nom affiché différent de l'adresse": "display name does not match the address",
    "logo de faible qualité": "low-quality logo",
    "mise en page différente de l'original": "layout differs from the genuine email",
    "absence de signature habituelle": "usual signature missing",
    "police non standard": "non-standard font",
    "formule générique (« Cher utilisateur »)": "generic greeting ('Dear user')",
    "demande inhabituelle": "unusual request",
    "incohérence de ton": "inconsistent tone",
    "urgence": "urgency",
    "menace de conséquence": "threat of consequences",
    "promesse de gain": "promise of a reward",
    "appel à l'autorité": "appeal to authority",
    "curiosité": "curiosity",
}
CUE_TYPE = {
    "fr": {"error": "Erreurs", "technical_indicator": "Indices techniques",
           "visual_presentation": "Présentation", "language_content": "Langage et contenu",
           "common_tactic": "Ressorts de manipulation"},
    "en": {"error": "Errors", "technical_indicator": "Technical indicators",
           "visual_presentation": "Visual presentation", "language_content": "Language and content",
           "common_tactic": "Manipulation tactics"},
}
TXT = {
    "fr": {"title": "C'était un exercice", "intro": "Ce message faisait partie d'un exercice "
           "de sensibilisation de l'équipe Sécurité. Aucune donnée n'a été transmise, et "
           "personne n'est jugé : ces e-mails sont conçus pour être crédibles.",
           "theme": "Thème", "cues": "Les indices que l'on pouvait repérer",
           "none": "Aucun indice visible : celui-ci était vraiment difficile.",
           "do": "Le bon réflexe", "steps": ["Au moindre doute, cliquez sur **Signaler**.",
           "Si vous avez saisi un mot de passe, prévenez l'équipe Sécurité : pas de reproche, "
           "on agit juste plus vite.", "Vérifiez par un autre canal (téléphone, intranet) "
           "toute demande inhabituelle."]},
    "en": {"title": "This was an exercise", "intro": "This message was part of a Security "
           "team awareness exercise. No data was sent, and nobody is being judged: these "
           "emails are designed to be convincing.", "theme": "Theme",
           "cues": "The clues you could have spotted",
           "none": "No visible clue: this one was genuinely hard.",
           "do": "The right reflex", "steps": ["When in doubt, click **Report**.",
           "If you entered a password, tell the Security team: no blame, we just act faster.",
           "Check any unusual request through another channel (phone, intranet)."]},
}


def landing_page(campaign: dict, lang: str) -> str:
    t = TXT[lang]
    theme = campaign["theme_fr"] if lang == "fr" else campaign["theme_en"]
    L = [f"# {t['title']}", "", t["intro"], "", f"**{t['theme']} :** {theme}"
         if lang == "fr" else f"**{t['theme']}:** {theme}", "", f"## {t['cues']}", ""]
    any_cue = False
    for ctype, items in campaign["cues"].items():
        if not items:
            continue
        any_cue = True
        names = items if lang == "fr" else [CUE_EN[x] for x in items]
        L.append(f"- **{CUE_TYPE[lang][ctype]}** : " + ", ".join(names)
                 if lang == "fr" else f"- **{CUE_TYPE[lang][ctype]}**: " + ", ".join(names))
    if not any_cue:
        L.append(t["none"])
    L += ["", f"## {t['do']}", ""] + [f"{i}. {s}" for i, s in enumerate(t["steps"], 1)]
    return "\n".join(L) + "\n"
