# -*- coding: utf-8 -*-

'''
    NetMozi Addon
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
import os, time, json, xbmcgui
from resources.lib.modules import control

watchedFile = os.path.join(control.dataPath, 'watched.json')

playingProperty = 'netmozi.playing'

# a lejatszas inditasa es a service elso ellenorzese kozt eltelhet ennyi masodperc
maxPlayingAge = 120


def load():
    try:
        file = open(watchedFile, "r")
        items = json.load(file)
        file.close()
        return items
    except:
        return {}


def add(key):
    items = load()
    if key in items:
        return
    items[key] = 1
    control.makeFile(control.dataPath)
    file = open(watchedFile, "w")
    json.dump(items, file)
    file.close()


def clear():
    try:
        control.idle()

        yes = control.yesnoDialog('Megnézett-nyilvántartás törlése', 'Biztos benne? A Kodi saját megnézett-jelzéseit ez nem érinti.', '')
        if not yes: return

        if os.path.exists(watchedFile):
            os.remove(watchedFile)

        control.infoDialog(u'Folyamat befejez\u0151d\u00F6tt')
    except:
        pass


def setPlaying(key):
    xbmcgui.Window(10000).setProperty(playingProperty, '%d|%s' % (int(time.time()), key))


def getPlaying():
    home = xbmcgui.Window(10000)
    value = home.getProperty(playingProperty)
    home.clearProperty(playingProperty)
    if not value:
        return None
    stamp, sep, key = value.partition('|')
    try:
        if time.time() - int(stamp) > maxPlayingAge:
            return None
    except:
        return None
    return key
