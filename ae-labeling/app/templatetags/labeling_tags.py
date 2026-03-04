from django import template
from django.conf import settings

from app.models import Document

register = template.Library()


@register.inclusion_tag("label_widget.html")
def render_label_widget(doc: Document):
    original_predictions = doc.original_predictions
    return_dict = {}

    labels = settings.AE_LABELS
    for label in labels:
        return_dict[label] = {
            "score": original_predictions[f"{label}_score"],
            "bar_size": int(original_predictions[f"{label}_score"] * 100),
            "pred": original_predictions[f"{label}_pred"],
            "pretty_name": label.replace("_", " ").capitalize(),
        }

    return {"preds": return_dict}
