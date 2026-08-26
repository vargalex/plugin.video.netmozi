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

import xbmc
from resources.lib.modules import watched

# ennyi lejatszott resz felett szamit a film/epizod megnezettnek
watchedRatio = 0.9

pollInterval = 5

monitor = xbmc.Monitor()
player = xbmc.Player()

xbmc.log('NetMozi: service elindult', xbmc.LOGINFO)

# None = nem a mi lejatszasunk fut, '' = fut valami, de nem a mienk
currentKey = None
currentProgress = 0

while not monitor.abortRequested():
    if player.isPlayingVideo():
        if currentKey is None:
            currentKey = watched.getPlaying() or ''
        if currentKey:
            try:
                total = player.getTotalTime()
                if total > 0:
                    currentProgress = float(player.getTime()) / total
            except:
                pass
    elif currentKey is not None:
        if currentKey and currentProgress >= watchedRatio:
            watched.add(currentKey)
            xbmc.log('NetMozi: megnezettnek jelolve: %s' % currentKey, xbmc.LOGINFO)
        currentKey = None
        currentProgress = 0

    if monitor.waitForAbort(pollInterval):
        break
