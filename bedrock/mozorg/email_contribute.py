# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import namedtuple

from django.core.mail import EmailMessage

import basket
import jingo
import requests
from jinja2.exceptions import TemplateNotFound

from lib.l10n_utils.dotlang import _lazy as _


fa = namedtuple('FunctionalArea', ['id', 'name', 'subject', 'contacts'])
LANG_FILES = 'mozorg/contribute'
FUNCTIONAL_AREAS = (
    fa('support',
        _('Helping Users'),
        'Support',
        ['jay@jaygarcia.com', 'rardila@mozilla.com', 'madasan@gmail.com'],
    ),
    fa('qa',
        _('Testing and QA'),
        'QA',
        ['qa-contribute@mozilla.org'],
    ),
    fa('coding',
        _('Coding'),
        'Coding',
        ['josh@joshmatthews.net'],
    ),
    fa('marketing',
        _('Marketing'),
        'Marketing',
        ['marketing-get-involved@mozilla.com'],
    ),
    fa('localization',
        _('Localization and Translation'),
        'Localization',
        ['rardila@mozilla.com', 'jbeatty@mozilla.com', 'arky@mozilla.com'],
    ),
    fa('webdev',
        _('Web Development'),
        'Webdev',
        ['lcrouch@mozilla.com'],
    ),
    fa('addons',
        _('Add-ons'),
        'Add-ons',
        ['atsay@mozilla.com'],
    ),
    fa('design',
        _('Visual Design'),
        'Design',
        ['mnovak@mozilla.com'],
    ),
    fa('documentation',
        _('Documentation and Writing'),
        'Documentation',
        ['jswisher@mozilla.com'],
    ),
    fa('education',
        _('Education'),
        'Education',
        ['makerparty@mozilla.org'],
    ),
    fa('other',
        _('Other'),
        '',
        ['dboswell@mozilla.com'],
    ),
    fa('suggestions',
        _('I have a suggestion for Firefox'),
        'Firefox Suggestions',
        ['jay@jaygarcia.com'],
    ),
    fa('issues',
        _('I need help with a Firefox issue'),
        'Firefox issue',
        ['jay@jaygarcia.com'],
    ),
)

INTEREST_CHOICES = (('', _('Area of interest?')),) + tuple(
                    (area.id, area.name) for area in FUNCTIONAL_AREAS)
FUNCTIONAL_AREAS_DICT = dict((area.id, area) for area in FUNCTIONAL_AREAS)

LOCALE_CONTACTS = {
    'bg': ['community@bgzilla.org'],
    'bn-BD': ['mahayalamkhan@gmail.com'],
    'cs': ['info@mozilla.cz'],
    'de': ['contribute@mozilla.de'],
    'el': ['core@mozilla-greece.org'],
    'es-AR': ['participa@mozilla-hispano.org'],
    'es-CL': ['participa@mozilla-hispano.org'],
    'es-ES': ['participa@mozilla-hispano.org'],
    'es-MX': ['participa@mozilla-hispano.org'],
    'fr': ['contact@mozfr.org'],
    'fy-NL': ['fryskefirefox@gmail.com'],
    'hr': ['contribute@mozilla-hr.org'],
    'id': ['info@mozilla.web.id'],
    'it': ['collabora@mozillaitalia.org'],
    'lt': ['prisijunk@mozilla.lt'],
    'ms': ['community@mozilla.my'],
    'nl': ['contribute@mozilla-nl.org'],
    'pl': ['chcepomoc@aviary.pl'],
    'pt-BR': ['envolva-se-mozilla-brasil@googlegroups.com'],
    'ro': ['contact@mozilla.ro'],
    'ru': ['contribute@mozilla-russia.org'],
    'sl': ['info@mozilla.si'],
    'sq': ['besnik@mozilla-albania.org'],
    'sr': ['prikljucise@mozilla-srbija.org'],
    'ta': ['vallavan2valluvan@gmail.com'],
    'tr': ['bilgi@mozilla.org.tr'],
    'zh-CN': ['contributor-zh-cn@mozilla.org'],
    'zh-TW': ['contribute@mail.moztw.org'],
}


def handle_form(request, form):
    if form.is_valid():
        data = form.cleaned_data
        send(request, data)
        autorespond(request, data)

        if data.get('newsletter', False):
            if data.get('interest', False) == 'education':
                # custom-1788 is the privacy policy checkbox on this page
                payload = {'email': data['email'], 'custom-1788': '1'}
                try:
                    requests.post('https://sendto.mozilla.org/page/s/mentor-signup',
                                  data=payload, timeout=2)
                except requests.exceptions.RequestException:
                    pass
            else:
                try:
                    basket.subscribe(data['email'], 'about-mozilla')
                except basket.BasketException:
                    pass

        return True
    return False


def send(request, data):
    """Forward contributor's email to our contacts.

    All emails are sent to contribute@mozilla.org

    For locales with points of contact, it is also sent to them.
    For locales without, it is also sent to functional area contacts.
    """
    functional_area = FUNCTIONAL_AREAS_DICT[data['interest']]

    from_ = 'contribute-form@mozilla.org'
    subject = 'Inquiry about Mozilla %s' % functional_area.subject
    msg = jingo.render_to_string(request, 'mozorg/emails/infos.txt', data)
    headers = {'Reply-To': data['email']}

    to = ['contribute@mozilla.org']

    cc = None
    if request.locale in LOCALE_CONTACTS:
        cc = LOCALE_CONTACTS[request.locale]
    else:
        cc = functional_area.contacts

    email = EmailMessage(subject, msg, from_, to, cc=cc, headers=headers)
    email.send()


def autorespond(request, data):
    """Send an auto-respond email based on chosen field of interest and locale.

    You can add localized responses by creating email messages in
    mozorg/emails/<category.txt>
    """
    functional_area = FUNCTIONAL_AREAS_DICT[data['interest']]

    subject = 'Inquiry about Mozilla %s' % functional_area.subject
    to = [data['email']]
    from_ = 'contribute-form@mozilla.org'
    reply_to = ['contribute@mozilla.org']
    headers = {}
    msg = ''

    template = 'mozorg/emails/%s.txt' % functional_area.id
    if request.locale != 'en-US' and request.locale in LOCALE_CONTACTS:
        template = '%s/templates/%s' % (request.locale, template)
        reply_to += LOCALE_CONTACTS[request.locale]
    else:
        reply_to += functional_area.contacts

    try:
        msg = jingo.render_to_string(request, template, data)
    except TemplateNotFound:
        # No template found means no auto-response
        return False

    # FIXME Why ?
    msg = msg.replace('\n', '\r\n')
    headers = {'Reply-To': ','.join(reply_to)}

    email = EmailMessage(subject, msg, from_, to, headers=headers)
    email.send()
