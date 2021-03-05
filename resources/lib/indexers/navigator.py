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
import os,sys,re,xbmc,xbmcgui,xbmcplugin,xbmcaddon, time, locale, base64
import urlresolver
from resources.lib.modules import client
from resources.lib.modules.utils import py2_encode

if sys.version_info[0] == 3:
    import urllib.parse as urlparse
    from urllib.parse import quote_plus
else:
    import urlparse
    from urllib import quote_plus

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
addonFanart = xbmcaddon.Addon().getAddonInfo('fanart')

base_url = 'https://netmozi.com/'

class navigator:
    def __init__(self):
        try:
            locale.setlocale(locale.LC_ALL, "")
        except:
            pass
        self.username = xbmcaddon.Addon().getSetting('username')
        self.password = xbmcaddon.Addon().getSetting('password')
        self.logincookie = base64.b64decode(xbmcaddon.Addon().getSetting('logincookie')).decode('utf-8')
        self.base_path = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
        self.searchFileName = os.path.join(self.base_path, "search.history")

    def root(self):
        menuItems = {'base&type=1': 'Filmek', 'base&type=2': 'Sorozatok', 'search': 'Keresés'}
        for menuItem in sorted(menuItems):
            self.addDirectoryItem(menuItems[menuItem], menuItem, '', 'DefaultFolder.png')
        self.endDirectory()

    def getSearches(self):
        self.addDirectoryItem('Új keresés', 'newsearch', '', 'DefaultFolder.png')
        try:
            file = open(self.searchFileName, "r")
            items = file.read().splitlines()
            items.sort(cmp=locale.strcoll)
            file.close()
            for item in items:
                self.addDirectoryItem(item, 'movies&page=1&type=&order=1&search=%s' % (quote_plus(item)), '', 'DefaultFolder.png')
            if len(items) > 0:
                self.addDirectoryItem('Keresési előzmények törlése', 'deletesearchhistory', '', 'DefaultFolder.png') 
        except:
            pass   
        self.endDirectory()

    def getOrderTypes(self, tipus):
        url_content = client.request(base_url)
        btnGroup = client.parseDOM(url_content, 'div', attrs={'class': 'btn-group'})[0]
        labels = client.parseDOM(btnGroup, 'label')
        for label in labels:
            name = client.parseDOM(label, 'input', attrs={'class': 'orderRadioInput'})
            if len(name) > 0:
                name = name[0].strip()
                order = client.parseDOM(label, 'input', attrs={'class': 'orderRadioInput'}, ret='value')[0]
                self.addDirectoryItem(name, 'movies&page=1&type=%s&order=%s&search=' % (tipus, order), '', 'DefaultFolder.png')
        self.endDirectory()

    def deleteSearchHistory(self):
        if os.path.exists(self.searchFileName):
            os.remove(self.searchFileName)

    def doSearch(self):
        search_text = self.getSearchText()
        if search_text != '':
            if not os.path.exists(self.base_path):
                os.mkdir(self.base_path)
            file = open(self.searchFileName, "a")
            file.write("%s\n" % search_text)
            file.close()
            self.getMovies('', 1, 1, search_text)

    def getInfo(self, sm8, searchStr):
        result = "0"
        rows=client.parseDOM(sm8, 'div', attrs={'class': 'row'})
        for row in rows:
            divs=client.parseDOM(row, 'div')
            if searchStr in py2_encode(divs[0]):
                result=py2_encode(divs[1]).strip()
        return result

    def getMovies(self, tipus, page, order, search):
        if search == None:
            search = ''
        url_content = client.request('%s?page=%s&type=%s&order=%s&search=%s' % (base_url, page, tipus, order, quote_plus(search)))
        movies = client.parseDOM(url_content, 'div', attrs={'class': 'col-sm-4 col_main'})
        if len(movies)>0:
            for movie in movies:
                tempTitle = client.parseDOM(movie, 'div', attrs={'class': 'col_name'})[0]
                title = py2_encode(client.replaceHTMLCodes(tempTitle)).replace('<small>(sorozat)</small>', '')
                isSorozat = "(sorozat)" in tempTitle
                sorozatLabel = ''
                if isSorozat and tipus != "2":
                    sorozatLabel = ' [COLOR yellow][I]sorozat[/I][/COLOR]'
                url = client.parseDOM(movie, 'a', attrs={'class': 'col_a'}, ret='href')[0]
                thumbDiv = client.parseDOM(movie, 'div', attrs={'class': 'col-sm-6'})[0]
                thumb = 'https:'+client.parseDOM(thumbDiv, 'img', ret='src')[0]
                infoDiv = client.parseDOM(movie, 'div', attrs={'class': 'col-sm-6'})[1]
                infoRows = client.parseDOM(infoDiv, 'div', attrs={'class': 'row'})
                year = re.sub('<.*>', '', py2_encode(client.replaceHTMLCodes(infoRows[0]))).strip()
                duration = int(re.sub('<.*>', '', py2_encode(client.replaceHTMLCodes(infoRows[1]))).strip().replace(' perc',''))*60
                linkcount = re.sub('<.*>', '', py2_encode(client.replaceHTMLCodes(infoRows[2]))).strip().replace('db', '')
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
        title = py2_encode(client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0])).strip()        
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
        plot = self.getInfo(temp, 'Leírás')
        duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
        thumb = 'https:'+client.parseDOM(temp, 'img', ret='src')[0]
        series = client.parseDOM(url_content, 'ul', attrs={'id': 'seasonUl'})
        series = client.parseDOM(series, 'a')
        for serie in series:
            self.addDirectoryItem('%s. évad' % py2_encode(serie), 'episodes&url=%s&serie=%s' % (url, serie), thumb, 'DefaultTVShows.png', meta={'title': '%s - %s. évad' % (title, py2_encode(serie)), 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def getEpisodes(self, url, serie):
        url_content = client.request(url)
        self.Login()
        url_content = client.request('%s%s' %(base_url, url), cookie=self.logincookie)
        container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
        temp = client.parseDOM(container, 'h3')[0]
        title = py2_encode(client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0])).strip()        
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
        plot = self.getInfo(temp, 'Leírás')
        duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
        thumb = 'https:'+client.parseDOM(temp, 'img', ret='src')[0]
        episodes = client.parseDOM(url_content, 'ul', attrs={'id': 'seasonUl%s' % serie})
        episodes = client.parseDOM(episodes, 'a')
        for episode in episodes:
            self.addDirectoryItem('%s. rész' % py2_encode(episode), 'movie&url=%s/s%s/e%s' % (url, serie, episode), thumb, 'DefaultTVShows.png', meta={'title': '%s - %s. évad %s. rész' % (title, serie, py2_encode(episode)), 'plot': plot, 'duration': duration, 'fanart': thumb})
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
            title = py2_encode(client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0])).strip()
            temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
            thumb = 'https:'+client.parseDOM(temp, 'img', ret='src')[0]
            temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
            plot = self.getInfo(temp, 'Leírás')
            duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
            serieInfo = client.parseDOM(url_content, 'h4')
            if serieInfo:
                serieInfo=' - %s' % py2_encode(serieInfo[0])
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
                    url=urlparse.urljoin('%s://%s' % (mURL.scheme, mURL.netloc),py2_encode(client.parseDOM(cols[3], 'a', attrs={'class': 'btn btn-outline-primary btn-sm'}, ret='href')[0]))
                    quality=py2_encode(cols[4])
                    site=py2_encode(cols[5])
                    self.addDirectoryItem('%s | [B]%s[/B] | [COLOR limegreen]%s[/COLOR] | [COLOR blue]%s[/COLOR] %s' % (format(sourceCnt, '02'), site, nyelv, quality, valid), 'playmovie&url=%s' % url, thumb, 'DefaultMovies.png', isFolder=False, meta={'title': title + serieInfo, 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def playmovie(self, url):
        self.Login()
        xbmc.log('NetMozi: Try to play from URL: %s' % url, xbmc.LOGINFO)
        final_url = client.request(url, cookie=self.logincookie, output="geturl")
        xbmc.log('NetMozi: final URL: %s' % final_url, xbmc.LOGINFO)
        try:
            direct_url = urlresolver.resolve(final_url)
            if direct_url:
                xbmc.log('NetMozi: URLResolver resolved URL: %s' % direct_url, xbmc.LOGINFO)
                direct_url = py2_encode(direct_url)
            else:
                xbmc.log('NetMozi: URLResolver could not resolve url: %s' % final_url, xbmc.LOGINFO)
                xbmcgui.Dialog().notification("URL feloldás hiba", "URL feloldása sikertelen a %s host-on" % urlparse.urlparse(final_url).hostname)
        except Exception as e:
            xbmc.log('NetMozi: URLResolver resolved URL: %s' % final_url, xbmc.LOGINFO)
            xbmcgui.Dialog().notification(urlparse.urlparse(url).hostname, str(e))
            return
        if direct_url:
            xbmc.log('NetMozi: playing URL: %s' % direct_url, xbmc.LOGINFO)
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
                xbmcaddon.Addon().setSetting('logincookie', base64.b64encode(login_cookies.encode('ascii')))
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
        if not context == None: cm.append((py2_encode(context[0]), 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))
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
