"""Form Engine : Gère les formulaires multi-étapes pour la saisie structurée."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FormStep(BaseModel):
    """Une étape d'un formulaire."""
    name: str = Field(description="Nom technique du champ (ex: fournisseur)")
    label: str = Field(description="Libellé affiché à l'utilisateur (ex: Fournisseur)")
    field_type: str = Field(description="Type de champ : text, number, select, date")
    options: Optional[List[str]] = Field(None, description="Liste des options pour un champ select")
    value: Optional[Any] = Field(None, description="Valeur saisie")


class PendingForm(BaseModel):
    """État d'un formulaire en cours de saisie."""
    form_id: str = Field(description="Identifiant du formulaire (ex: depense, operation)")
    title: str = Field(description="Titre affiché du formulaire")
    steps: List[FormStep] = Field(description="Liste des étapes")
    current_step: int = Field(default=0, description="Index de l'étape en cours")
    data: Dict[str, Any] = Field(default_factory=dict, description="Données collectées")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contexte (chantier_id, org_id...)")

    def current_step_name(self) -> Optional[str]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step].name
        return None

    def current_step_info(self) -> Optional[FormStep]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def get_current_prompt(self) -> str:
        step = self.current_step_info()
        if not step:
            return "Formulaire complété."
        total = len(self.steps)
        options_hint = ""
        if step.options:
            options_hint = f" ({', '.join(step.options)})"
        return f"📝 {self.title} — Étape {self.current_step + 1}/{total}\n{step.label}{options_hint} :"

    def advance(self, step_name: str, value: Any) -> str:
        if step_name != self.current_step_name():
            raise ValueError(f"Étape '{step_name}' invalide. Attendue : '{self.current_step_name()}'")
        self.data[step_name] = value
        self.current_step += 1
        return "ok"

    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)

    def progress(self) -> str:
        if self.is_complete():
            return "✅ Formulaire complété"
        return f"Étape {self.current_step + 1}/{len(self.steps)} : {self.steps[self.current_step].label}"

    def reset(self):
        self.current_step = 0
        self.data = {}


class FormEngine:
    """Moteur de gestion des formulaires multi-étapes."""

    @staticmethod
    def create_from_payload(payload: Dict[str, Any]) -> PendingForm:
        """Crée un PendingForm depuis le payload d'une action INIT_FORM."""
        steps = []
        for s in payload.get("steps", []):
            steps.append(FormStep(
                name=s["name"],
                label=s.get("label", s["name"]),
                field_type=s.get("type", "text"),
                options=FormEngine._normalize_options(s.get("options"))
            ))
        return PendingForm(
            form_id=payload.get("form_id", "unknown"),
            title=payload.get("title", "Formulaire"),
            steps=steps,
            metadata=payload.get("context", {})
        )

    @staticmethod
    def _normalize_options(options: Any) -> Optional[List[str]]:
        """Normalise les options d'un FormStep (accepte strings ou dicts avec label)."""
        if not options:
            return None
        result = []
        for opt in options:
            if isinstance(opt, str):
                result.append(opt)
            elif isinstance(opt, dict):
                result.append(opt.get("label", opt.get("value", str(opt))))
            else:
                result.append(str(opt))
        return result
