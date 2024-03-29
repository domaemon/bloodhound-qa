
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.

import sys

from genshi.builder import tag
from genshi.core import TEXT
from genshi.filters.transform import Transformer
from genshi.output import DocType

from trac.config import Option, BoolOption
from trac.core import *
from trac.config import ListOption
from trac.mimeview.api import get_mimetype
from trac.resource import Resource
from trac.ticket.api import TicketSystem
from trac.ticket.model import Ticket
from trac.ticket.notification import TicketNotifyEmail
from trac.ticket.web_ui import TicketModule
from trac.util.compat import set
from trac.util.translation import _
from trac.versioncontrol.web_ui.browser import BrowserModule
from trac.web.api import IRequestFilter, IRequestHandler, ITemplateStreamFilter
from trac.web.chrome import (add_script, add_stylesheet, INavigationContributor,
                             ITemplateProvider, prevnext_nav, Chrome)
from trac.wiki.admin import WikiAdmin

from themeengine.api import ThemeBase, ThemeEngineSystem

from bhdashboard.util import dummy_request
from bhdashboard.web_ui import DashboardModule
from bhdashboard import wiki

from pkg_resources import get_distribution
from urlparse import urlparse
from wsgiref.util import setup_testing_defaults

try:
    from multiproduct.ticket.web_ui import ProductTicketModule
except ImportError:
    ProductTicketModule = None

class BloodhoundTheme(ThemeBase):
    """Look and feel of Bloodhound issue tracker.
    """
    template = htdocs = css = screenshot = disable_trac_css = True
    disable_all_trac_css = True
    BLOODHOUND_KEEP_CSS = set(
        (
            'diff.css', 'code.css'
        )
    )
    BLOODHOUND_TEMPLATE_MAP = {
        # Admin
        'admin_basics.html' : ('bh_admin_basics.html', None),
        'admin_components.html' : ('bh_admin_components.html', None),
        'admin_enums.html' : ('bh_admin_enums.html', None),
        'admin_logging.html' : ('bh_admin_logging.html', None),
        'admin_milestones.html' : ('bh_admin_milestones.html', None),
        'admin_perms.html' : ('bh_admin_perms.html', None),
        'admin_plugins.html' : ('bh_admin_plugins.html', None),
        'admin_repositories.html' : ('bh_admin_repositories.html', None),
        'admin_versions.html' : ('bh_admin_versions.html', None),
        'admin_products.html' : ('bh_admin_products.html', None),

        # Preferences
        'prefs.html' : ('bh_prefs.html', None),
        'prefs_advanced.html' : ('bh_prefs_advanced.html', None),
        'prefs_datetime.html' : ('bh_prefs_datetime.html', None),
        'prefs_general.html' : ('bh_prefs_general.html', None),
        'prefs_language.html' : ('bh_prefs_language.html', None),
        'prefs_keybindings.html' : ('bh_prefs_keybindings.html', None),
        'prefs_pygments.html' : ('bh_prefs_pygments.html', None),
        'prefs_userinterface.html' : ('bh_prefs_userinterface.html', None),

        # Search
        'search.html' : ('bh_search.html', '_modify_search_data'),

        # Wiki
        'wiki_delete.html' : ('bh_wiki_delete.html', None),
        'wiki_diff.html' : ('bh_wiki_diff.html', None),
        'wiki_edit.html' : ('bh_wiki_edit.html', None),
        'wiki_rename.html' : ('bh_wiki_rename.html', None),
        'wiki_view.html' : ('bh_wiki_view.html', '_modify_wiki_page_path'),

        # Ticket
        'milestone_edit.html' : ('bh_milestone_edit.html', None),
        'milestone_delete.html' : ('bh_milestone_delete.html', None),
        'milestone_view.html' : ('bh_milestone_view.html', '_modify_roadmap_css'),
        'query.html' : ('bh_query.html', None),
        'report_delete.html' : ('bh_report_delete.html', None),
        'report_edit.html' : ('bh_report_edit.html', None), 
        'report_list.html' : ('bh_report_list.html', None),
        'report_view.html' : ('bh_report_view.html', None),
        'ticket.html' : ('bh_ticket.html', '_modify_ticket'),
        'ticket_preview.html' : ('bh_ticket_preview.html', None),
        'ticket_delete.html' : ('bh_ticket_delete.html', None),

        # Attachment
        'attachment.html' : ('bh_attachment.html', None),
        'preview_file.html' : ('bh_preview_file.html', None),

        # Version control
        'revisionlog.html' : ('bh_revisionlog.html', '_modify_browser'),
        'browser.html' : ('bh_browser.html', '_modify_browser'),
        'dir_entries.html' : ('bh_dir_entries.html', None),

        # Multi Product
        'product_view.html' : ('bh_product_view.html', None),

        # General purpose
        'about.html' : ('bh_about.html', None),
        'history_view.html' : ('bh_history_view.html', None),
        'timeline.html' : ('bh_timeline.html', None),

        # Account manager plugin
        'login.html' : ('bh_login.html', None),
    }
    BOOTSTRAP_CSS_DEFAULTS = (
        # ('XPath expression', ['default', 'bootstrap', 'css', 'classes'])
        ("body//table[not(contains(@class, 'table'))]", # TODO: Accurate ?
                ['table', 'table-condensed']),
    )
    
    labels_application_short = Option('labels', 'application_short', 
        'Bloodhound', """A short version of application name most commonly 
        displayed in text, titles and labels""")

    labels_application_full = Option('labels', 'application_full', 
        'Apache Bloodhound', """This is full name with trade mark and 
        everything, it is currently used in footers and about page only""")
    
    labels_footer_left_prefix = Option('labels', 'footer_left_prefix', '', 
        """Text to display before full application name in footers""")

    labels_footer_left_postfix = Option('labels', 'footer_left_postfix', '', 
        """Text to display after full application name in footers""")
    
    labels_footer_right = Option('labels', 'footer_right', '',
        """Text to use as the right aligned footer""")

    is_bhsearch_default = BoolOption('bhsearch', 'is_default', False)

    _wiki_pages = None
    Chrome.default_html_doctype = DocType.HTML5

    implements(IRequestFilter, INavigationContributor, ITemplateProvider,
               ITemplateStreamFilter)

    def _get_whitelabelling(self):
        """Gets the whitelabelling config values"""
        return dict(
            application_short = self.labels_application_short,
            application_full = self.labels_application_full,
            footer_left_prefix = self.labels_footer_left_prefix,
            footer_left_postfix = self.labels_footer_left_postfix,
            footer_right = self.labels_footer_right,
            application_version = application_version)

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        """Insert default Bootstrap CSS classes if rendering 
        legacy templates (i.e. determined by template name prefix) 
        and renames wiki guide links.
        """
        tx = Transformer('body')

        def add_classes(classes):
            """Return a function ensuring CSS classes will be there for element.
            """
            def attr_modifier(name, event):
                attrs = event[1][1]
                class_list = attrs.get(name, '').split()
                self.log.debug('BH Theme : Element classes ' + str(class_list))

                out_classes = ' '.join(set(class_list + classes))
                self.log.debug('BH Theme : Inserting class ' + out_classes)
                return out_classes
            return attr_modifier
        
        # Insert default bootstrap CSS classes if necessary
        for xpath, classes in self.BOOTSTRAP_CSS_DEFAULTS :
            tx = tx.end().select(xpath) \
                    .attr('class', add_classes(classes))
         
        # Rename wiki guide links
        tx = tx.end() \
            .select("body//a[contains(@href,'/wiki/%s')]" % wiki.GUIDE_NAME) \
            .map(lambda text: wiki.new_name(text), TEXT)

        # Rename trac error
        app_short = self.labels_application_short
        tx = tx.end() \
            .select("body//div[@class='error']/h1") \
            .map(lambda text: text.replace("Trac", app_short), TEXT)
                    
        return stream | tx

    # IRequestFilter methods

    def pre_process_request(self, req, handler):
        """Pre process request filter"""
        def hwiki(*args, **kw):

            def new_name(name):
                new_name = wiki.new_name(name)
                if new_name != name:
                    if not self._wiki_pages:
                        wiki_admin = WikiAdmin(self.env)
                        self._wiki_pages = wiki_admin.get_wiki_list()
                    if new_name in self._wiki_pages:
                        return new_name
                return name

            a = tuple([new_name(x) for x in args])
            return req.href.__call__("wiki", *a, **kw)

        req.href.wiki = hwiki
        
        return handler

    def post_process_request(self, req, template, data, content_type):
        """Post process request filter.
        Removes all trac provided css if required"""
        
        if template is None and data is None and sys.exc_info() == (None, None, None):
            return template, data, content_type
        
        def is_active_theme():
            is_active = False
            active_theme = ThemeEngineSystem(self.env).theme
            if active_theme is not None:
                this_theme_name = self.get_theme_names().next()
                is_active = active_theme['name'] == this_theme_name
            return is_active

        req.chrome['labels'] = self._get_whitelabelling()

        links = req.chrome.get('links',{})
        # replace favicon if appropriate
        if self.env.project_icon == 'common/trac.ico':
            bh_icon = 'theme/img/bh.ico'
            new_icon = {'href': req.href.chrome(bh_icon),
                        'type': get_mimetype(bh_icon)}
            if links.get('icon'):
                links.get('icon')[0].update(new_icon)
            if links.get('shortcut icon'):
                links.get('shortcut icon')[0].update(new_icon)
        
        is_active_theme = is_active_theme()
        if self.disable_all_trac_css and is_active_theme:
            if self.disable_all_trac_css:
                stylesheets = links.get('stylesheet',[])
                if stylesheets:
                    path = req.base_path + '/chrome/common/css/'
                    _iter = ([ss, ss.get('href', '')] for ss in stylesheets)
                    links['stylesheet'] = [ss for ss, href in _iter 
                            if not href.startswith(path) or
                            href.rsplit('/', 1)[-1] in self.BLOODHOUND_KEEP_CSS]
            template, modifier = self.BLOODHOUND_TEMPLATE_MAP.get(
                    template, (template, None))
            if modifier is not None:
                modifier = getattr(self, modifier)
                modifier(req, template, data, content_type, is_active_theme)

        if is_active_theme and data is not None:
            data['responsive_layout'] = self.env.config.getbool(
                    'bloodhound', 'responsive_layout', 'true')
            data['is_bhsearch_default'] = self.is_bhsearch_default

        return template, data, content_type

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        """Ensure dashboard htdocs will be there even if
        `bhdashboard.web_ui.DashboardModule` is disabled.
        """
        if not self.env.is_component_enabled(DashboardModule):
            return DashboardModule(self.env).get_htdocs_dirs()

    def get_templates_dirs(self):
        """Ensure dashboard templates will be there even if
        `bhdashboard.web_ui.DashboardModule` is disabled.
        """
        if not self.env.is_component_enabled(DashboardModule):
            return DashboardModule(self.env).get_templates_dirs()

    # Request modifiers

    def _modify_search_data(self, req, template, data, content_type, is_active):
        """Insert breadcumbs and context navigation items in search web UI
        """
        if is_active:
            # Insert query string in search box (see bloodhound_theme.html)
            req.search_query = data.get('query')
            # Breadcrumbs nav
            data['resourcepath_template'] = 'bh_path_search.html'
            # Context nav
            prevnext_nav(req, _('Previous'), _('Next'))

    def _modify_wiki_page_path(self, req, template, data, content_type, is_active):
        """Override wiki breadcrumbs nav items
        """
        if is_active:
            data['resourcepath_template'] = 'bh_path_wikipage.html'

    def _modify_roadmap_css(self, req, template, data, content_type, is_active):
        """Insert roadmap.css
        """
        add_stylesheet(req, 'dashboard/css/roadmap.css')

    def _modify_ticket(self, req, template, data, content_type, is_active):
        """Ticket modifications
        """
        self._modify_resource_breadcrumb(req, template, data, content_type,
                                         is_active)

    def _modify_resource_breadcrumb(self, req, template, data, content_type,
                                    is_active):
        """Provides logic for breadcrumb resource permissions
        """
        if data and ('ticket' in data.keys()) and data['ticket'].exists:
            data['resourcepath_template'] = 'bh_path_ticket.html'
            # determine path permissions
            for resname, permname in [('milestone', 'MILESTONE_VIEW'),
                                      ('product', 'PRODUCT_VIEW')]:
                res = Resource(resname, data['ticket'][resname])
                data['path_show_' + resname] = permname in req.perm(res)

    def _modify_browser(self, req, template, data, content_type, is_active):
        """Locate path to file in breadcrumbs area rather than title.
        Add browser-specific CSS.
        """
        data.update(dict(
                resourcepath_template='bh_path_links.html',
                path_depth_limit=2
            ))
        add_stylesheet(req, 'theme/css/browser.css')

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return

    def get_navigation_items(self, req):
        if 'BROWSER_VIEW' in req.perm and 'VERSIONCONTROL_ADMIN' in req.perm:
            bm = self.env[BrowserModule]
            if bm and not list(bm.get_navigation_items(req)):
                yield ('mainnav', 'browser', 
                       tag.a(_('Browse Source'),
                             href=req.href.wiki('TracRepositoryAdmin')))

class QuickCreateTicketDialog(Component):
    implements(IRequestFilter, IRequestHandler)

    qct_fields = ListOption('ticket', 'quick_create_fields', 
                            'product,version,type',
        doc="""Multiple selection fields displayed in create ticket menu""")

    # IRequestFilter(Interface):

    def pre_process_request(self, req, handler):
        """Nothing to do.
        """
        return handler

    def post_process_request(self, req, template, data, content_type):
        """Append necessary ticket data
        """
        try:
            tm = self._get_ticket_module()
        except TracError:
            # no ticket module so no create ticket button
            return template, data, content_type

        if (template, data, content_type) != (None,) * 3: # TODO: Check !
            if data is None:
                data = {}
            fakereq = dummy_request(self.env)
            ticket = Ticket(self.env)
            tm._populate(fakereq, ticket, False)
            all_fields = dict([f['name'], f] \
                              for f in tm._prepare_fields(fakereq, ticket) \
                              if f['type'] == 'select')
            data['qct'] = {'fields': [all_fields[k] for k in self.qct_fields
                                      if k in all_fields]}
        return template, data, content_type

    # IRequestHandler methods

    def match_request(self, req):
        """Handle requests sent to /qct
        """
        return req.path_info == '/qct'

    def process_request(self, req):
        """Forward new ticket request to `trac.ticket.web_ui.TicketModule`
        but return plain text suitable for AJAX requests.
        """
        try:
            tm = self._get_ticket_module()
            req.perm.require('TICKET_CREATE')
            summary = req.args.pop('field_summary', '')
            desc = ""
            attrs = dict([k[6:], v] for k,v in req.args.iteritems() \
                                    if k.startswith('field_'))
            ticket_id = self.create(req, summary, desc, attrs, True)
        except Exception, exc:
            self.log.exception("BH: Quick create ticket failed %s" % (exc,))
            req.send(str(exc), 'plain/text', 500)
        else:
            req.send(str(ticket_id), 'plain/text')

    def _get_ticket_module(self):
        ptm = None
        if ProductTicketModule is not None:
            ptm = self.env[ProductTicketModule]
        tm = self.env[TicketModule]
        if not (tm is None) ^ (ptm is None):
            raise TracError('Unable to load TicketModule (disabled)?')
        if tm is None:
            tm = ptm
        return tm

    # Public API
    def create(self, req, summary, description, attributes = {}, notify=False):
        """ Create a new ticket, returning the ticket ID. 

        PS: Borrowed from XmlRpcPlugin.
        """
        t = Ticket(self.env)
        t['summary'] = summary
        t['description'] = description
        t['reporter'] = req.authname
        for k, v in attributes.iteritems():
            t[k] = v
        t['status'] = 'new'
        t['resolution'] = ''
        t.insert()
        # Call ticket change listeners
        ts = TicketSystem(self.env)
        for listener in ts.change_listeners:
            listener.ticket_created(t)
        if notify:
            try:
                tn = TicketNotifyEmail(self.env)
                tn.notify(t, newticket=True)
            except Exception, e:
                self.log.exception("Failure sending notification on creation "
                                   "of ticket #%s: %s" % (t.id, e))
        return t.id

application_version = get_distribution('BloodhoundTheme').version
