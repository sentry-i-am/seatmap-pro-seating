from django import forms
from django.utils.translation import gettext_lazy as _

from .booking_api import DEFAULT_API_URL, checked_api_url


class ConnectionForm(forms.Form):
    api_url = forms.URLField(
        label=_('Booking API address'),
        initial=DEFAULT_API_URL,
        help_text=_('Change it only for an on-premise Seatmap Pro installation.'),
    )
    organization_token = forms.CharField(
        label=_('Organization token'),
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text=_('Stays on this server. Leave empty to keep the saved token.'),
    )
    public_key = forms.UUIDField(label=_('Public key'))
    event_id = forms.UUIDField(label=_('Seatmap Pro event ID'))

    def __init__(self, *args, token_saved=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_saved = token_saved

    def clean_api_url(self):
        try:
            return checked_api_url(self.cleaned_data['api_url'])
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error

    def clean_organization_token(self):
        token = self.cleaned_data['organization_token'].strip()
        if not token and not self.token_saved:
            raise forms.ValidationError(_('Enter the organization token.'))
        return token

    def clean(self):
        data = super().clean()
        for key in ('public_key', 'event_id'):
            if data.get(key):
                data[key] = str(data[key])
        return data


class MappingForm(forms.Form):
    def __init__(self, *args, categories, products, initial_mapping, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = categories
        for index, category in enumerate(categories):
            self.fields[f'category_{index}'] = forms.ModelChoiceField(
                label=category,
                queryset=products,
                required=False,
                initial=initial_mapping.get(category),
                empty_label=_('Not for sale'),
            )

    def mapping(self):
        return {category: self.cleaned_data[f'category_{index}'] for index, category in enumerate(self.categories)}
