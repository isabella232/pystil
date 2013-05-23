# -*- coding: utf-8 -*-
# Copyright (C) 2011-2013 by Florian Mounier, Kozea
# This file is part of pystil, licensed under a 3-clause BSD license.

from pystil.db import Visit
from pystil.tracking import Message
from pystil.aggregates import get_attribute_and_count
from pystil.context import Hdr, url, MESSAGE_QUEUE
from pystil.utils import on
from tornado.web import asynchronous, HTTPError
from sqlalchemy import desc, func
from datetime import date, timedelta, datetime

import os
import uuid
import pystil.charts


@url(r'/')
class Index(Hdr):
    def get(self):
        self.render(
            'index.html',
            visits=(self.db.query(Visit)
                    .order_by(Visit.date.desc())[:10]))


@url(r'/pystil.js')
class PystilJs(Hdr):
    def get(self):
        self.set_header("Content-Type", 'application/javascript')
        js = os.path.join(
            self.application.settings['static_path'],
            'js', 'tracker.js')
        base_url = '%s://%s/' % (self.request.protocol, self.request.host)
        with open(js) as js_file:
            self.write(js_file.read() % (base_url, str(uuid.uuid4())))


@url(r'/pystil-(\d+).gif')
class Tracker(Hdr):

    @asynchronous
    def get(self, stamp):
        self.set_header("Content-Type", 'image/gif')
        gif_fn = os.path.join(
            self.application.settings['static_path'], 'pystil.gif')

        with open(gif_fn, 'rb') as gif_file:
            self.write(gif_file.read())
        self.finish()
        message = Message(
            self.log,
            self.request.arguments,
            self.request.headers['User-Agent'],
            self.request.headers.get(
                'X-FORWARDED-FOR', self.request.remote_ip))
        self.log.debug('Inserting message for %s (Already in queue %s)' % (
            message.ip, MESSAGE_QUEUE.qsize()))
        MESSAGE_QUEUE.put(message, True)
        self.log.debug('Message for %s inserted' % message.ip)


@url(r'/visit/(\d+)')
class ViewVisit(Hdr):
    def get(self, visit_id):
        """List of sites"""
        visit = self.db.query(Visit).get(visit_id)
        self.render('visit.html', visit=visit)


@url(r'/criterion/(offset/\d+/)?([^/]+)/(.+)')
class Criterion(Hdr):
    def get(self, offset, criterion, value):
        """Visits by criterion"""
        if offset:
            offset = int(offset.replace('offset/', '').rstrip('/'))
        else:
            offset = 0

        available_criteria = sorted(filter(
            lambda x: not x.startswith('_') and not x in (
                'client_tz_offset', 'pretty_referrer', 'referrer_domain',
                'spent_time', 'metadata'
            ), dir(Visit)))

        if criterion not in available_criteria:
            raise HTTPError(404)

        if criterion == 'date':
            try:
                value = datetime.strptime(
                    value.replace('+', ' '), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime('%Y-%m-%d')
                except ValueError:
                    value = datetime.now()
            filter_ = func.date_trunc('DAY', Visit.date) == value.date()
        elif criterion in (
                'referrer', 'asn', 'browser_name', 'site',
                'browser_version', 'browser_name_version', 'query'):
            filter_ = getattr(Visit, criterion).ilike('%%%s%%' % value)
        else:
            filter_ = func.lower(getattr(Visit, criterion)) == value.lower()
        self.render(
            'criterion.html',
            visits=(
                self.db
                .query(Visit)
                .filter(filter_)
                .order_by(desc(Visit.date)))[offset:offset + 20],
            criterion=criterion, value=value,
            available_criteria=available_criteria)


@url(r'/sites')
class Sites(Hdr):
    def get(self):
        """List of sites"""
        table, attr, countcol = get_attribute_and_count('domain')
        sites = (
            self.db
            .query(attr, countcol.label('count'))
            .group_by(attr)
            .order_by(desc(countcol)))[:20]
        all_ = self.db.query(countcol).scalar()
        self.render('sites.html', sites=sites, all_=all_)


@url(r'/sites/(.+)')
class SitesQuery(Hdr):
    def get(self, query):
        """Sites matching query"""
        table, attr, countcol = get_attribute_and_count('domain')
        sites = (
            self.db
            .query(attr.label('host'), countcol.label('count'))
            .filter(attr.like('%%%s%%' % query))
            .group_by(attr)
            .order_by(desc(countcol)))[:20]

        all_ = self.db.query(countcol).scalar()
        self.render('sites_table.html', sites=sites, all_=all_)


@url(r'/site/([^/]+)/([^/]*)')
class Site(Hdr):
    def kwargs(self, site, page):
        kwargs = {
            'page': page,
            'site': site
        }
        page = page or '/visits'
        if page == 'last':
            kwargs['visits'] = (
                self.db.query(Visit)
                .filter(on(site))
                .order_by(Visit.date.desc())[:10])
        kwargs['kwargs'] = kwargs
        return kwargs

    def get(self, site, page):
        """Stats per site or all if site = all"""
        self.render('site/_base.html', **self.kwargs(site, page))

    def post(self, site, page):
        self.render('site/%s.html' % page, **self.kwargs(site, page))


@url(r'/load/data/([^/]+)/([^/]+)/([^/]+)'
     '(/between/\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2})?'
     '(/in/\w{2})?.svg')
class LoadData(Hdr):
    def get(self, site, type_, criteria, dates=None, lang=None):
        self.set_header("Content-Type", "image/svg+xml")
        if lang:
            lang = lang.replace('/in/', '')
        else:
            lang = 'us'
        chart = getattr(pystil.charts, type_)(
            self.db, site, criteria, None, None, '%s://%s' % (
                self.request.protocol, self.request.host), lang)
        self.write(chart.render_load())


@url(r'/data/([^/]+)/([^/]+)/([^/]+)'
     '(/between/\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2})?'
     '(/in/\w{2})?.svg')
class Data(Hdr):
    def get(self, site, type_, criteria, dates=None, lang=None):
        self.set_header("Content-Type", "image/svg+xml")
        if lang:
            lang = lang.replace('/in/', '')
        else:
            lang = 'us'
        if dates:
            from_date, to_date = dates.replace('/between/', '').split('/')
            from_date = date(*map(int, from_date.split('-')))
            to_date = date(*map(int, to_date.split('-')))
        else:
            from_date = date.today() - timedelta(days=31)
            to_date = date.today()
        chart = getattr(pystil.charts, type_)(
            self.db, site, criteria, from_date, to_date, '%s://%s' % (
                self.request.protocol, self.request.host), lang)
        self.write(chart.render())
