import os
import pytest
from app.services.agents.form_engine import FormEngine, PendingForm, FormStep

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


@pytest.fixture
def depense_form():
    return PendingForm(
        form_id="depense",
        title="Nouvelle dépense",
        steps=[
            FormStep(name="fournisseur", label="Fournisseur", field_type="text"),
            FormStep(name="montant", label="Montant (€)", field_type="number"),
            FormStep(name="categorie", label="Catégorie", field_type="select", options=["fournisseur", "sous_traitant", "autre"]),
        ],
        metadata={"chantier_id": "CH-001", "org_id": "org_123"}
    )


def test_form_engine_initial_state(depense_form):
    """Un formulaire fraîchement créé est sur la première étape."""
    assert depense_form.current_step == 0
    assert depense_form.current_step_name() == "fournisseur"
    assert depense_form.is_complete() is False
    assert depense_form.progress() == "Étape 1/3 : Fournisseur"


def test_form_engine_advances_step(depense_form):
    """Avancer remplit la donnée et passe à l'étape suivante."""
    result = depense_form.advance("fournisseur", "Batimat")
    assert result == "ok"
    assert depense_form.data["fournisseur"] == "Batimat"
    assert depense_form.current_step == 1
    assert depense_form.current_step_name() == "montant"


def test_form_engine_completes_sequence(depense_form):
    """Après avoir rempli toutes les étapes, le formulaire est complet."""
    depense_form.advance("fournisseur", "Batimat")
    depense_form.advance("montant", "150.0")
    depense_form.advance("categorie", "fournisseur")

    assert depense_form.is_complete() is True
    assert depense_form.progress() == "✅ Formulaire complété"
    assert depense_form.data == {
        "fournisseur": "Batimat",
        "montant": "150.0",
        "categorie": "fournisseur"
    }


def test_form_engine_get_next_step_prompt(depense_form):
    """Le moteur retourne le libellé de l'étape en cours."""
    prompt = depense_form.get_current_prompt()
    assert "Fournisseur" in prompt
    assert "1/3" in prompt


def test_form_engine_reset(depense_form):
    """Réinitialiser le formulaire vide les données et revient à l'étape 0."""
    depense_form.advance("fournisseur", "Batimat")
    depense_form.reset()
    assert depense_form.current_step == 0
    assert depense_form.data == {}
    assert depense_form.is_complete() is False


def test_form_engine_auto_detect_select(depense_form):
    """Si l'étape a des options, le moteur le signale."""
    step = depense_form.steps[2]
    assert step.field_type == "select"
    assert step.options == ["fournisseur", "sous_traitant", "autre"]


def test_form_engine_invalid_step_name(depense_form):
    """Avancer avec un nom d'étape invalide lève une erreur."""
    with pytest.raises(ValueError, match="Étape 'inconnu' invalide"):
        depense_form.advance("inconnu", "valeur")
