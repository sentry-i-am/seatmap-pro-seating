from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from .booking_api import SeatmapApiError
from .compat import event_products, host_attr
from .forms import ConnectionForm, MappingForm
from .importer import (
    SETTING_KEYS,
    apply_layout,
    current_mapping,
    fetch_layout,
    pending_layout,
    save_settings,
    setting,
)

EventPermissionRequiredMixin = host_attr('control.permissions', 'EventPermissionRequiredMixin')
EventSettingsViewMixin = host_attr('control.views.event', 'EventSettingsViewMixin')
SeatProtected = host_attr('base.services.seating', 'SeatProtected')


class SettingsView(EventPermissionRequiredMixin, EventSettingsViewMixin, TemplateView):
    permission = 'can_change_event_settings'
    template_name = 'seatmap_pro/settings.html'

    def dispatch(self, request, *args, **kwargs):
        if 'seatmap_pro' not in request.event.get_plugins():
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def connection_form(self, data=None):
        event = self.request.event
        initial = {key: setting(event, key) for key in SETTING_KEYS if key != 'organization_token'}
        initial['api_url'] = initial['api_url'] or ConnectionForm.base_fields['api_url'].initial
        return ConnectionForm(data, initial=initial, token_saved=bool(setting(event, 'organization_token')))

    def mapping_form(self, layout, data=None):
        event = self.request.event
        return MappingForm(
            data,
            categories=[category['name'] for category in layout['categories']],
            products=event_products(event).all(),
            initial_mapping=current_mapping(event),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        layout = pending_layout(self.request.event)
        context.setdefault('connection_form', self.connection_form())
        if layout and 'mapping_form' not in context:
            context['mapping_form'] = self.mapping_form(layout)
        context['pending_layout'] = layout
        context['seat_count'] = self.request.event.seats.filter(subevent=None).count()
        context['plan'] = self.request.event.seating_plan
        return context

    def post(self, request, *args, **kwargs):
        event = request.event
        if event.has_subevents:
            messages.error(request, _('Event series are not supported yet.'))
            return redirect(request.path)
        if request.POST.get('action') == 'apply':
            return self.apply()
        form = self.connection_form(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(connection_form=form))
        save_settings(event, form.cleaned_data)
        try:
            layout = fetch_layout(event)
        except (SeatmapApiError, ValueError, KeyError) as error:
            messages.error(request, _('The venue could not be loaded: %(error)s') % {'error': error})
            return redirect(request.path)
        seats = sum(len(row['seats']) for zone in layout['zones'] for row in zone['rows'])
        messages.success(request, _('Loaded %(count)s seats. Assign a product to each category.') % {'count': seats})
        return redirect(request.path)

    def apply(self):
        event = self.request.event
        layout = pending_layout(event)
        if not layout:
            return redirect(self.request.path)
        form = self.mapping_form(layout, self.request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(mapping_form=form))
        try:
            apply_layout(event, self.request.organizer, layout, form.mapping())
        except SeatProtected as error:
            messages.error(self.request, str(error))
            return redirect(self.request.path)
        messages.success(self.request, _('The seating plan is saved.'))
        return redirect(self.request.path)
