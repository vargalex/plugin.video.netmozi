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


import os,sys,re,xbmc,xbmcgui,xbmcplugin,xbmcaddon,urllib,urlparse,base64,time
import urlresolver
from resources.lib.modules import client

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
addonFanart = xbmcaddon.Addon().getAddonInfo('fanart')

base_url = 'aHR0cHM6Ly9uZXRtb3ppLmNvbS8='.decode('base64')

class navigator:
    def __init__(self):
        self.username = xbmcaddon.Addon().getSetting('username')
        self.password = xbmcaddon.Addon().getSetting('password')
        self.logincookie = xbmcaddon.Addon().getSetting('logincookie').decode('base64')

    def root(self):
        menuItems = {'base&type=1': 'Filmek', 'base&type=2': 'Sorozatok', 'keres': 'Keresés'}
        for menuItem in sorted(menuItems):
            self.addDirectoryItem(menuItems[menuItem], menuItem, '', 'DefaultFolder.png')
        self.endDirectory()

    def getOrderTypes(self, tipus):
        url_content = client.request(base_url)
        btnGroup = client.parseDOM(url_content, 'div', attrs={'class': 'btn-group'})[0]
        labels = client.parseDOM(btnGroup, 'label')
        for label in labels:
            name = client.parseDOM(label, 'input', attrs={'class': 'orderRadioInput'})
            if len(name) > 0:
                name = name[0].strip()
                order = client.parseDOM(label, 'input', attrs={'class': 'orderRadioInput'}, ret='value')
                self.addDirectoryItem(name, 'movies&page=1&type=%s&order=%s&search=' % (tipus, order), '', 'DefaultFolder.png')
        self.endDirectory()

    def doSearch(self):
        search_text = self.getSearchText()
        if search_text != '':
            self.getMovies('', 1, 1, urllib.quote_plus(search_text))

    def getInfo(self, sm8, searchStr):
        result = "0"
        rows=client.parseDOM(sm8, 'div', attrs={'class': 'row'})
        for row in rows:
            divs=client.parseDOM(row, 'div')
            if searchStr in divs[0].encode('utf-8'):
                result=divs[1].encode('utf-8').strip()
        return result

    def getMovies(self, tipus, page, order, search):
        if search == None:
            search = ''
        url_content = client.request('%s?page=%s&type=%s&order=%s&search=%s' % (base_url, page, tipus, order, search))
        movies = client.parseDOM(url_content, 'div', attrs={'class': 'col-sm-4 col_main'})
        if len(movies)>0:
            for movie in movies:
                tempTitle = client.parseDOM(movie, 'div', attrs={'class': 'col_name'})[0]
                title = client.replaceHTMLCodes(tempTitle).encode('utf-8').replace('<small>(sorozat)</small>', '')
                isSorozat = "(sorozat)" in tempTitle
                sorozatLabel = ''
                if isSorozat and tipus != "2":
                    sorozatLabel = ' [COLOR yellow][I]sorozat[/I][/COLOR]'
                url = client.parseDOM(movie, 'a', attrs={'class': 'col_a'}, ret='href')[0]
                thumbDiv = client.parseDOM(movie, 'div', attrs={'class': 'col-sm-6'})[0]
                thumb = 'https:'+client.parseDOM(thumbDiv, 'img', ret='src')[0]
                infoDiv = client.parseDOM(movie, 'div', attrs={'class': 'col-sm-6'})[1]
                infoRows = client.parseDOM(infoDiv, 'div', attrs={'class': 'row'})
                year = re.sub('<.*>', '', client.replaceHTMLCodes(infoRows[0]).encode('utf-8')).strip()
                duration = int(re.sub('<.*>', '', client.replaceHTMLCodes(infoRows[1]).encode('utf-8')).strip().replace(' perc',''))*60
                linkcount = re.sub('<.*>', '', client.replaceHTMLCodes(infoRows[2]).encode('utf-8')).strip().replace('db', '')
                action='series' if isSorozat else 'movie'
                self.addDirectoryItem('%s (%s)%s | [COLOR limegreen]%s link[/COLOR]' %(title, year, sorozatLabel, linkcount), '%s&url=%s' % (action, url), thumb, 'DefaultMovies.png' if isSorozat else 'DefaultTVShows.png', meta={'title': title, 'duration': duration, 'fanart': thumb})
            pager = client.parseDOM(url_content, 'select', attrs={'name': 'page'})[0]
            options = client.parseDOM(pager, 'option', ret='value')
            if (int(options[-1]) > int(page)):
                self.addDirectoryItem(u'[I]K\u00F6vetkez\u0151 oldal  (%d/%s)>>[/I]' %(int(page)+1, options[-1]), 'movies&page=%d&type=%s&order=%s&search=%s' % (int(page)+1, tipus, order, search), '', 'DefaultFolder.png')
            self.endDirectory(type="movies")
        else:
            xbmcgui.Dialog().ok('NetMozi', 'Nem található forrás!')
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())

    def getSeries(self, url):
        self.Login()
        url_content = client.request('%s%s' %(base_url, url), cookie=self.logincookie)
        container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
        temp = client.parseDOM(container, 'h3')[0]
        title = client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0]).encode('utf-8').strip()        
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
        plot = self.getInfo(temp, 'Leírás')
        duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
        thumb = 'https:'+client.parseDOM(temp, 'img', ret='src')[0]
        series = client.parseDOM(url_content, 'ul', attrs={'id': 'seasonUl'})
        series = client.parseDOM(series, 'a')
        for serie in series:
            self.addDirectoryItem('%s. évad' % serie.encode('utf-8'), 'episodes&url=%s&serie=%s' % (url, serie), thumb, 'DefaultTVShows.png', meta={'title': '%s - %s. évad' % (title, serie.encode('utf-8')), 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def getEpisodes(self, url, serie):
        url_content = client.request(url)
        self.Login()
        url_content = client.request('%s%s' %(base_url, url), cookie=self.logincookie)
        container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
        temp = client.parseDOM(container, 'h3')[0]
        title = client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0]).encode('utf-8').strip()        
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
        plot = self.getInfo(temp, 'Leírás')
        duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
        thumb = 'https:'+client.parseDOM(temp, 'img', ret='src')[0]
        episodes = client.parseDOM(url_content, 'ul', attrs={'id': 'seasonUl%s' % serie})
        episodes = client.parseDOM(episodes, 'a')
        for episode in episodes:
            self.addDirectoryItem('%s. rész' % episode.encode('utf-8'), 'movie&url=%s/s%s/e%s' % (url, serie, episode), thumb, 'DefaultTVShows.png', meta={'title': '%s - %s. évad %s. rész' % (title, serie, episode.encode('utf-8')), 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def getMovie(self, url):
        self.Login()
        url_content = client.request('%s%s' %(base_url, url), cookie=self.logincookie)
        if "regeljbe.png" in url_content:
            xbmcgui.Dialog().ok('NetMozi', 'Lista lekérés sikertelen. A hozzáféréshez regisztráció szükséges.')
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
        else:
            movieURL = 'https:%s' % client.parseDOM(url_content, 'a', attrs={'class': 'details_links_btn'}, ret='href')[0]
            container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
            temp = client.parseDOM(container, 'h3')[0]
            title = client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0]).encode('utf-8').strip()
            temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
            thumb = 'https:'+client.parseDOM(temp, 'img', ret='src')[0]
            temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
            plot = self.getInfo(temp, 'Leírás')
            duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
            serieInfo = client.parseDOM(url_content, 'h4')
            if serieInfo:
                serieInfo=' - %s' % serieInfo[0].encode('utf-8')
            else:
                serieInfo=''
            url_content = client.request(movieURL)
            table = client.parseDOM(url_content, 'table', attrs={'class': 'table table-responsive'})
            if table:
                rows = client.parseDOM(table, 'tr')
                sourceCnt = 0
                for row in rows:
                    sourceCnt+=1
                    cols = client.parseDOM(row, 'td')
                    if 'hungary.gif' in cols[0]:
                        nyelv = 'Szinkron'
                    elif 'usa.gif' in cols[0]:
                        nyelv='Külfüldi'
                    elif 'uk-hu.png' in cols[0]:
                        nyelv = 'Felirat'
                    else:
                        nyelv = 'Ismeretlen'
                    valid = ''
                    if 'red_mark.png' in cols[1]:
                        valid = '| [COLOR red]Érvénytelen[/COLOR]'
                    mURL = urlparse.urlsplit(movieURL)
                    url=urlparse.urljoin('%s://%s' %(mURL.scheme, mURL.netloc),client.parseDOM(cols[3], 'a', attrs={'class': 'btn btn-outline-primary btn-sm'}, ret='href')[0].encode('utf-8'))
                    quality=cols[4].encode('utf-8')
                    site=cols[5].encode('utf-8')
                    self.addDirectoryItem('%s | [B]%s[/B] | [COLOR limegreen]%s[/COLOR] | [COLOR blue]%s[/COLOR] %s' % (format(sourceCnt, '02'), site, nyelv, quality, valid), 'playmovie&url=%s' % url, thumb, 'DefaultMovies.png', isFolder=False, meta={'title': title + serieInfo, 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def playmovie(self, url):
        url_content = client.request(url, cookie=self.logincookie)
        matches = re.search(r'^(.*)var link(.*)= "(.*)";(.*)$', url_content, re.MULTILINE)
        if matches:
            url = matches.group(3).decode('base64')
            xbmc.log('NetMozi: resolving url: %s' % url, xbmc.LOGNOTICE)
            try:
                direct_url = urlresolver.resolve(url)
                if direct_url:
                    direct_url = direct_url.encode('utf-8')
            except Exception as e:
                xbmcgui.Dialog().notification(urlparse.urlparse(url).hostname, e.message)
                return
            if direct_url:
                xbmc.log('NetMozi: playing URL: %s' % direct_url, xbmc.LOGNOTICE)
                play_item = xbmcgui.ListItem(path=direct_url)
                xbmcplugin.setResolvedUrl(syshandle, True, listitem=play_item)

    def Login(self):
        if (self.username and self.password) != '':
            try:
                t1 = int(xbmcaddon.Addon().getSetting('logintimestamp'))
            except:
                t1 = 0
            t2 = int(time.time())
            update = (abs(t2 - t1) / 3600) >= 24 or t1 == 0
            if update == False and self.logincookie != "":
                return
            login_url = '%s/login/do' % base_url
            login_cookies = client.request(login_url, post="username=%s&password=%s" % (self.username, self.password), output='cookie')
            if 'ca' in login_cookies:
                xbmcaddon.Addon().setSetting('logintimestamp', str(t2))
                xbmcaddon.Addon().setSetting('logincookie', base64.b64encode(login_cookies))
                self.logincookie=login_cookies
            else:
                xbmcgui.Dialog().ok(u'NetMozi', u'Bejelentkez\u00E9si hiba!')
                xbmcaddon.Addon().setSetting('logintimestamp', '0')
                xbmcaddon.Addon().setSetting('logincookie', '')
                self.logincookie = ""
        return

    def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True, Fanart=None, meta=None):
        url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
        if thumb == '': thumb = icon
        cm = []
        if queue == True: cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))
        if not context == None: cm.append((context[0].encode('utf-8'), 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))
        item = xbmcgui.ListItem(label=name)
        item.addContextMenuItems(cm)
        item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb})
        if Fanart == None: Fanart = addonFanart
        item.setProperty('Fanart_Image', Fanart)
        if isFolder == False: item.setProperty('IsPlayable', 'true')
        if not meta == None: item.setInfo(type='Video', infoLabels = meta)
        xbmcplugin.addDirectoryItem(handle=syshandle, url=url, listitem=item, isFolder=isFolder)


    def endDirectory(self, type='addons'):
        xbmcplugin.setContent(syshandle, type)
        #xbmcplugin.addSortMethod(syshandle, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(syshandle, cacheToDisc=True)

    def getSearchText(self):
        search_text = ''
        keyb = xbmc.Keyboard('',u'Add meg a keresend\xF5 film c\xEDm\xE9t')
        keyb.doModal()

        if (keyb.isConfirmed()):
            search_text = keyb.getText()

        return search_text
