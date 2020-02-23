# -*- coding: utf-8 -*-

'''
    NetMozi Add-on
    Copyright (C) 2020

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import urlparse,sys, xbmcgui

params = dict(urlparse.parse_qsl(sys.argv[2].replace('?','')))

action = params.get('action')

tipus = params.get('type')

page = params.get('page')

order = params.get('order')

url = params.get('url')

search = params.get('search')

serie = params.get('serie')

if action == None:
    from resources.lib.indexers import navigator
    navigator.navigator().root()

elif action == 'base':
    from resources.lib.indexers import navigator
    navigator.navigator().getOrderTypes(tipus)


elif action == 'movies':
    from resources.lib.indexers import navigator
    navigator.navigator().getMovies(tipus, page, order, search)

elif action == 'movie':
    from resources.lib.indexers import navigator
    navigator.navigator().getMovie(url)

elif action == 'playmovie':
    from resources.lib.indexers import navigator
    navigator.navigator().playmovie(url)

elif action == 'keres':
    from resources.lib.indexers import navigator
    navigator.navigator().doSearch()

elif action == 'series':
    from resources.lib.indexers import navigator
    navigator.navigator().getSeries(url)

elif action == 'episodes':
    from resources.lib.indexers import navigator
    navigator.navigator().getEpisodes(url, serie)