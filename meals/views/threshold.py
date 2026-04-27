import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import viewsets, filters

from ..models import ThresholdPreset
from ..nutrients import NUTRIENTS
from ..serializers import ThresholdPresetSerializer


class ThresholdPresetViewSet(viewsets.ModelViewSet):
    queryset = ThresholdPreset.objects.all()
    serializer_class = ThresholdPresetSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


@login_required
def threshold_preset_list(request):
    nutrients_list = [
        {"key": key, "label": str(meta["label"]), "unit": meta["unit"]}
        for key, meta in NUTRIENTS.items()
    ]
    i18n = {
        "searchPlaceholder": _("Search presets…"),
        "createPreset": _("Create Preset"),
        "noData": _("No threshold presets found."),
        "colName": _("Name"),
        "networkError": _("Network error"),
        "newPresetName": _("New Preset"),
        "errorCreate": _("Error creating preset"),
        "showMore": _("Show more nutrients"),
        "showLess": _("Show less"),
    }
    return render(
        request,
        "meals/threshold_preset_list.html.j2",
        {
            "nutrients_json": json.dumps(nutrients_list),
            "i18n_json": json.dumps({k: str(v) for k, v in i18n.items()}),
            "preset_editor_base_url": reverse("threshold-preset-list").rstrip("/")
            + "/",
        },
    )


@login_required
def threshold_preset_editor(request, pk):
    get_object_or_404(ThresholdPreset, pk=pk)
    nutrients_list = [
        {"key": key, "label": str(meta["label"]), "unit": meta["unit"]}
        for key, meta in NUTRIENTS.items()
    ]
    i18n = {
        "saved": _("Saved"),
        "saving": _("Saving…"),
        "errorSaving": _("Error saving"),
        "backToList": _("Threshold Presets"),
        "min": _("Min"),
        "max": _("Max"),
        "deletePreset": _("Delete preset"),
        "deleteConfirm": _("Delete this preset?"),
        "networkError": _("Network error"),
        "showMore": _("Show more nutrients"),
        "showLess": _("Show less"),
        "notFound": _("Preset not found."),
        "mustBeValidNumber": _("Must be a valid number."),
        "mustBeLessThanMax": _("Must be less than max ({max})."),
        "mustBeGreaterThanMin": _("Must be greater than min ({min})."),
    }
    return render(
        request,
        "meals/threshold_preset_editor.html.j2",
        {
            "preset_id": pk,
            "nutrients_json": json.dumps(nutrients_list),
            "i18n_json": json.dumps({k: str(v) for k, v in i18n.items()}),
            "preset_list_url": reverse("threshold-preset-list"),
        },
    )
