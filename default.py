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


import sys
from resources.lib.indexers import navigator

if sys.version_info[0] == 3:
    from urllib.parse import parse_qsl
else:
    from urlparse import parse_qsl


params = dict(parse_qsl(sys.argv[2].replace('?', '', 1)))

action = params.get('action')

tipus = params.get('type')

page = params.get('page')

order = params.get('order')

url = params.get('url')

search = params.get('search')

serie = params.get('serie')

subtitled = params.get('subtitled') == 'true'

if action == None:
    navigator.navigator().root()

elif action == 'base':
    navigator.navigator().getOrderTypes(tipus)


elif action == 'movies':
    navigator.navigator().getMovies(tipus, page, order, search)

elif action == 'movie':
    navigator.navigator().getMovie(url)

elif action == 'playmovie':
    navigator.navigator().playmovie(url, subtitled)

elif action == 'search':
    navigator.navigator().getSearches()

elif action == 'series':
    navigator.navigator().getSeries(url)

elif action == 'episodes':
    navigator.navigator().getEpisodes(url, serie)

elif action == 'newsearch':
    navigator.navigator().doSearch()

elif action == 'deletesearchhistory':
    navigator.navigator().deleteSearchHistory()

elif action == 'clearcache':
    navigator.navigator().clearCache()
