import os
import pytest
from app.services.agents.form_engine import PendingForm, FormStep, FormEngine

os.environ["GOOGLE_API_KEY"] = "fake-key"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/fake-credentials.json"


def test_callback_routes_to_form_step():
    """Un callback de type 'act:fournisseur' est routé vers l'étape correspondante du formulaire."""
    form = PendingForm(
        form_id="depense",
        title="Nouvelle dépense",
        steps=[
            FormStep(name="fournisseur", label="Fournisseur", field_type="text"),
            FormStep(name="montant", label="Montant (€)", field_type="number"),
        ],
        current_step=0,
        metadata={"chantier_id": "CH-001"}
    )

    callback_data = "act:fournisseur"

    step_name = callback_data.split(":")[1]
    assert step_name == form.current_step_name()


def test_form_advance_with_callback_value():
    """Avancer le formulaire avec une valeur de callback (text tapé ou clic)."""
    form = PendingForm(
        form_id="depense",
        title="Nouvelle dépense",
        steps=[
            FormStep(name="fournisseur", label="Fournisseur", field_type="text"),
            FormStep(name="montant", label="Montant (€)", field_type="number"),
        ],
        metadata={"chantier_id": "CH-001"}
    )

    form.advance("fournisseur", "Batimat")
    assert form.current_step_name() == "montant"
    assert form.data["fournisseur"] == "Batimat"
