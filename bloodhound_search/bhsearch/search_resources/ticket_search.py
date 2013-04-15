#!/usr/bin/env python
# -*- coding: UTF-8 -*-

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

r"""Ticket specifics for Bloodhound Search plugin."""
from bhsearch import BHSEARCH_CONFIG_SECTION
from bhsearch.api import ISearchParticipant, BloodhoundSearchApi, \
    IIndexParticipant, IndexFields
from bhsearch.search_resources.base import BaseIndexer, BaseSearchParticipant
from genshi.builder import tag
from trac.ticket.api import ITicketChangeListener, TicketSystem
from trac.ticket import Ticket
from trac.ticket.query import Query
from trac.config import ListOption, Option
from trac.core import implements

TICKET_TYPE = u"ticket"

class TicketFields(IndexFields):
    SUMMARY = "summary"
    MILESTONE = 'milestone'
    COMPONENT = 'component'
    KEYWORDS = "keywords"
    RESOLUTION = "resolution"
    CHANGES = 'changes'
    OWNER = 'owner'

class TicketIndexer(BaseIndexer):
    implements(ITicketChangeListener, IIndexParticipant)

    optional_fields = {
        'component': TicketFields.COMPONENT,
        'description': TicketFields.CONTENT,
        'keywords': TicketFields.KEYWORDS,
        'milestone': TicketFields.MILESTONE,
        'summary': TicketFields.SUMMARY,
        'status': TicketFields.STATUS,
        'resolution': TicketFields.RESOLUTION,
        'reporter': TicketFields.AUTHOR,
        'owner': TicketFields.OWNER,
    }

    def __init__(self):
        self.fields = TicketSystem(self.env).get_ticket_fields()
        self.text_area_fields = set(
            f['name'] for f in self.fields if f['type'] =='textarea')

    #ITicketChangeListener methods
    def ticket_created(self, ticket):
        """Index a recently created ticket."""
        self._index_ticket(ticket)

    def ticket_changed(self, ticket, comment, author, old_values):
        """Reindex a recently modified ticket."""
        # pylint: disable=unused-argument
        self._index_ticket(ticket)

    def ticket_deleted(self, ticket):
        """Called when a ticket is deleted."""
        try:
            search_api = BloodhoundSearchApi(self.env)
            search_api.delete_doc(TICKET_TYPE, ticket.id)
        except Exception, e:
            if self.silence_on_error:
                self.log.error("Error occurs during deleting ticket. \
                    The error will not be propagated. Exception: %s", e)
            else:
                raise

    def reindex_tickets(self, search_api, operation_context, milestone=None):
        for ticket in self._fetch_tickets(milestone):
            self._index_ticket(ticket, search_api, operation_context)

    def _fetch_tickets(self, milestone = None):
#        with self.env.db_transaction as db:
        for ticket_id in self._fetch_ids(milestone):
            yield Ticket(self.env, ticket_id)

    def _fetch_ids(self, milestone):
        sql = "SELECT id FROM ticket"
        args = []
        conditions = []
        if milestone:
            args.append(milestone)
            conditions.append("milestone=%s")
        if conditions:
            sql = sql + " WHERE " + " AND ".join(conditions)
        for row in self.env.db_query(sql, args):
            yield int(row[0])


    def _index_ticket(
            self, ticket, search_api = None, operation_context = None):
        try:
            if not search_api:
                search_api = BloodhoundSearchApi(self.env)
            doc = self.build_doc(ticket)
            search_api.add_doc(doc, operation_context)
        except Exception, e:
            if self.silence_on_error:
                self.log.error("Error occurs during ticket indexing. \
                    The error will not be propagated. Exception: %s", e)
            else:
                raise

    #IIndexParticipant members
    def build_doc(self, trac_doc):
        ticket = trac_doc
        doc = {
            IndexFields.ID: str(ticket.id),
            IndexFields.TYPE: TICKET_TYPE,
            IndexFields.TIME: ticket.time_changed,
            }

        for field, index_field in self.optional_fields.iteritems():
            if field in ticket.values:
                field_content = ticket.values[field]
                if field in self.text_area_fields:
                    field_content = self.wiki_formatter.format(field_content)
                doc[index_field] = field_content

        doc[TicketFields.CHANGES] = u'\n\n'.join(
            [self.wiki_formatter.format(x[4]) for x in ticket.get_changelog()
             if x[2] == u'comment'])
        return doc

    def get_entries_for_index(self):
        for ticket in self._fetch_tickets():
            yield self.build_doc(ticket)

    def _load_ticket_ids(self):
        query = Query(self.env, cols=['id'], order='id')
        return query.execute()


class TicketSearchParticipant(BaseSearchParticipant):
    implements(ISearchParticipant)

    participant_type = TICKET_TYPE
    required_permission = 'TICKET_VIEW'

    default_facets = [
        TicketFields.STATUS,
        TicketFields.MILESTONE,
        TicketFields.COMPONENT,
        ]
    default_grid_fields = [
        TicketFields.ID,
        TicketFields.SUMMARY,
        TicketFields.STATUS,
        TicketFields.MILESTONE,
        TicketFields.COMPONENT,
        ]
    prefix = TICKET_TYPE

    default_facets = ListOption(
        BHSEARCH_CONFIG_SECTION,
        prefix + '_default_facets',
        default=",".join(default_facets),
        doc="""Default facets applied to search view of specific resource""")

    default_view = Option(
        BHSEARCH_CONFIG_SECTION,
        prefix + '_default_view',
        doc = """If true, show grid as default view for specific resource in
            Bloodhound Search results""")

    default_grid_fields = ListOption(
        BHSEARCH_CONFIG_SECTION,
        prefix + '_default_grid_fields',
        default = ",".join(default_grid_fields),
        doc="""Default fields for grid view for specific resource""")

    #ISearchParticipant members
    def get_title(self):
        return "Ticket"

    def format_search_results(self, res):
        if not TicketFields.STATUS in res:
            stat = 'undefined_status'
            css_class = 'undefined_status'
        else:
            css_class = res[TicketFields.STATUS]
            if res[TicketFields.STATUS] == 'closed':
                resolution = ""
                if 'resolution' in res:
                    resolution = res['resolution']
                stat = '%s: %s' % (res['status'], resolution)
            else:
                stat = res[TicketFields.STATUS]

        id = res['hilited_id'] or res['id']
        id = tag.span('#', id, class_=css_class)
        summary = res['hilited_summary'] or res['summary']
        return tag(id, ': ', summary, ' (%s)' % stat)

