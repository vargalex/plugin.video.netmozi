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
import os,sys,re,xbmc,xbmcgui,xbmcplugin,xbmcaddon, locale, base64, random, string, json
import resolveurl
from resources.lib.modules import client, control, cache
from resources.lib.modules.utils import py2_encode, py2_decode, safeopen

if sys.version_info[0] == 3:
    import urllib.parse as urlparse
    from urllib.parse import quote_plus
else:
    import urlparse
    from urllib import quote_plus

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
addonFanart = xbmcaddon.Addon().getAddonInfo('fanart')

base_url = 'https://netmozi.com/'
track_url = '%s/visitortracker/track' % base_url

class navigator:

    def generate_random_string(self, length):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    def generate_visitorId(self):
        return self.generate_random_string(18)

    def generate_fingerprint(self):
        return self.generate_random_string(65)

    def __init__(self):
        try:
            locale.setlocale(locale.LC_ALL, "hu_HU.UTF-8")
        except:
            try:
                locale.setlocale(locale.LC_ALL, "")
            except:
                pass
        self.username = xbmcaddon.Addon().getSetting('username')
        self.password = xbmcaddon.Addon().getSetting('password')
        self.downloadsubtitles = xbmcaddon.Addon().getSettingBool('downloadsubtitles')
        self.base_path = py2_decode(control.transPath(control.addonInfo('profile')))
        self.searchFileName = os.path.join(self.base_path, "search.history")
        self.visitorId = cache.get(self.generate_visitorId, 24)
        self.fingerprint = cache.get(self.generate_fingerprint, 24)

    def root(self):
        menuItems = {'base&type=1': 'Filmek', 'base&type=2': 'Sorozatok', 'search': 'Keresés'}
        for menuItem in sorted(menuItems):
            self.addDirectoryItem(menuItems[menuItem], menuItem, '', 'DefaultFolder.png')
        self.endDirectory()

    def getSearches(self):
        self.addDirectoryItem('[COLOR lightgreen]Új keresés[/COLOR]', 'newsearch', '', 'DefaultFolder.png')
        try:
            file = open(self.searchFileName, "r")
            olditems = file.read().splitlines()
            file.close()
            items = list(set(olditems))
            items.sort(key=locale.strxfrm)
            if len(items) != len(olditems):
                file = open(self.searchFileName, "w")
                file.write("\n".join(items))
                file.close()
            for item in items:
                self.addDirectoryItem(item, 'movies&page=1&type=&order=1&search=%s' % (quote_plus(item)), '', 'DefaultFolder.png')
            if len(items) > 0:
                self.addDirectoryItem('[COLOR red]Keresési előzmények törlése[/COLOR]', 'deletesearchhistory', '', 'DefaultFolder.png')
        except:
            pass   
        self.endDirectory()

    def getOrderTypes(self, tipus):
        url_content = client.request(base_url, cookie=self.getSiteCookies())
        select = client.parseDOM(url_content, 'select', attrs={'id': 'order_by_select'})[0]
        matches=re.findall(r'<option value="([0-9])"(.*)>(.*)</option>', select)
        for match in matches:
                self.addDirectoryItem(match[2], 'movies&page=1&type=%s&order=%s&search=' % (tipus, match[0]), '', 'DefaultFolder.png')
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
        url_content = client.request('%s?page=%s&type=%s&order=%s&search=%s' % (base_url, page, tipus, order, quote_plus(search)), cookie=self.getSiteCookies())
        movies = client.parseDOM(url_content, 'div', attrs={'class': 'col-12.*?'})
        if len(movies)>0:
            for movie in movies:
                tempTitle = client.parseDOM(movie, 'div', attrs={'class': 'col_name'})[0]
                title = py2_encode(client.replaceHTMLCodes(tempTitle)).replace('<small>(sorozat)</small>', '').strip()
                isSorozat = "(sorozat)" in tempTitle
                sorozatLabel = ''
                if isSorozat and tipus != "2":
                    sorozatLabel = ' [COLOR yellow][I]sorozat[/I][/COLOR]'
                url = client.parseDOM(movie, 'a', attrs={'class': 'col_a'}, ret='href')[0]
                try:
                    thumbDiv = client.parseDOM(movie, 'div', attrs={'class': 'col-sm-6'})[0]
                    thumb = client.parseDOM(thumbDiv, 'img', ret='src')[0]
                    if thumb.startswith("//"):
                        thumb = "https:%s" % thumb
                except:
                    thumb = None
                try:
                    infoDiv = client.parseDOM(movie, 'div', attrs={'class': 'col-sm-6'})[1]
                except:
                    infoDiv = None
                try:
                    infoRows = client.parseDOM(infoDiv, 'div', attrs={'class': 'row'})
                except:
                    infoRows = None
                try:
                    year = "(%s)" % re.sub('<.*>', '', py2_encode(client.replaceHTMLCodes(infoRows[0]))).strip()
                except:
                    year = ""
                try:
                    duration = int(re.sub('<.*>', '', py2_encode(client.replaceHTMLCodes(infoRows[1]))).strip().replace(' perc',''))*60
                except:
                    duration = 0
                try:
                    linkcount = " | [COLOR limegreen]%s link[/COLOR]" % re.sub('<.*>', '', py2_encode(client.replaceHTMLCodes(infoRows[2]))).strip().replace('db', '')
                except:
                    linkcount = ""
                action='series' if isSorozat else 'movie'
                self.addDirectoryItem('%s %s%s%s' % (title, year, sorozatLabel, linkcount), '%s&url=%s' % (action, url), thumb, 'DefaultMovies.png' if isSorozat else 'DefaultTVShows.png', meta={'title': title, 'duration': duration, 'fanart': thumb})
            pager = client.parseDOM(url_content, 'select', attrs={'name': 'page'})[0]
            options = client.parseDOM(pager, 'option', ret='value')
            if (int(options[-1]) > int(page)):
                self.addDirectoryItem(u'[I]K\u00F6vetkez\u0151 oldal  (%d/%s)>>[/I]' %(int(page)+1, options[-1]), 'movies&page=%d&type=%s&order=%s&search=%s' % (int(page)+1, tipus, order, search), '', 'DefaultFolder.png')
            self.endDirectory(type="movies")
        else:
            xbmcgui.Dialog().ok('NetMozi', 'Nem található forrás!')
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())

    def getSeries(self, url):
        url_content = client.request('%s%s' %(base_url, url), cookie=self.getSiteCookies())
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
        url_content = client.request('%s%s' %(base_url, url), cookie=self.getSiteCookies())
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
        try:
            trackingData = json.loads(client.request(track_url, post='{"visitor_id": "%s", "fingerprint": "%s"}' % (self.visitorId, self.fingerprint)))
            if trackingData["status"] != "ok":
                xbmcgui.Dialog().ok('NetMozi', 'Hiba a tracking adatok lekérésekor!')
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
                return
            url_content = client.request('%s%s' %(base_url, url), cookie="%s; _vt_track=%s;" % (self.getSiteCookies(), trackingData["visitor_id"]))
        except:
            url_content = client.request('%s%s' %(base_url, url), cookie="%s;" % (self.getSiteCookies()))
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
            card = client.parseDOM(url_content, 'div', attrs={'class': 'card .+?'})[0]
            tableDiv = client.parseDOM(card, 'div', attrs={'class': 'table-responsive'})[0]
            table = client.parseDOM(tableDiv, 'table', attrs={'class': 'table'})
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
                    url=urlparse.urljoin('%s://%s' % (mURL.scheme, mURL.netloc),py2_encode(client.parseDOM(cols[3], 'a', attrs={'class': 'btn btn-outline-primary btn-sm action-btn'}, ret='href')[-1]))
                    quality=py2_encode(cols[4].strip())
                    site=py2_encode(cols[5].strip())
                    self.addDirectoryItem('%s | [B]%s[/B] | [COLOR limegreen]%s[/COLOR] | [COLOR blue]%s[/COLOR] %s' % (format(sourceCnt, '02'), site, nyelv, quality, valid), 'playmovie&url=%s&subtitled=%s' % (url, 'true' if nyelv == 'Felirat' else 'false'), thumb, 'DefaultMovies.png', isFolder=False, meta={'title': title + serieInfo, 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def playmovie(self, url, subtitled):
        xbmc.log('NetMozi: Try to play from URL: %s' % url, xbmc.LOGINFO)
        final_url = client.request(url, cookie=self.getSiteCookies(), output="geturl", error=True)
        if final_url:
            if "mindjart.megnezed" in final_url:
                url_content = client.request(final_url)
                matches = re.search(r'^(.*)function counter(.*)var link([^=]*)=([^"]*)"([^"]*)";(.*)$', url_content, re.S)
                if matches:
                    final_url = base64.b64decode(matches.group(5)).decode('utf-8')
                else:
                    data = re.search(r'<iframe[^>]*src=[\'"]([^\'"]+)[\'"]', url_content, re.IGNORECASE)
                    if data:
                        final_url = data.group(1)
                    else:
                        xbmc.log('NetMozi: cannot find <iframe[^>]*src="([^"]+)" in %s' % final_url)
        else:
            xbmcgui.Dialog().ok('NetMozi', 'Törölt tartalom!')
            return
        xbmc.log('NetMozi: final_url: %s' % final_url, xbmc.LOGINFO)
        if "streamplay" in final_url or "sbot" in final_url:
            html = client.request(final_url)
            from resolveurl.lib import jsunhunt
            if jsunhunt.detect(html):
                html = jsunhunt.unhunt(html)
                match=re.search(r'.*setAttribute\("src","([^"]*)".*', html)
                if match:
                    newURL = urlparse.urljoin(final_url, match.group(1))
                    final_url = client.request(newURL, output="geturl")
        xbmc.log('NetMozi: final URL: %s' % final_url, xbmc.LOGINFO)
        hmf = resolveurl.HostedMediaFile(final_url, subs=self.downloadsubtitles)
        subtitles = None
        if hmf:
            try:
                resp = hmf.resolve()
            except:
                xbmcgui.Dialog().ok("NetMozi", "ResolveURL hiba: Forrás feloldása sikertelen!")
                return
            if self.downloadsubtitles:
                direct_url = resp.get('url')
            else:
                direct_url = resp
            xbmc.log('NetMozi: ResolveURL resolved URL: %s' % direct_url, xbmc.LOGINFO)
            direct_url = py2_encode(direct_url)
            if self.downloadsubtitles:
                subtitles = resp.get('subs')
            play_item = xbmcgui.ListItem(path=direct_url)
            if 'm3u8' in direct_url:
                from inputstreamhelper import Helper
                is_helper = Helper('hls')
                if is_helper.check_inputstream():
                    if sys.version_info < (3, 0):  # if python version < 3 is safe to assume we are running on Kodi 18
                        play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')   # compatible with Kodi 18 API
                    else:
                        play_item.setProperty('inputstream', 'inputstream.adaptive')  # compatible with recent builds Kodi 19 API
                    try:
                        play_item.setProperty('inputstream.adaptive.stream_headers', direct_url.split("|")[1])
                        play_item.setProperty('inputstream.adaptive.manifest_headers', direct_url.split("|")[1])
                        play_item.setProperty('inputstream.adaptive.license_key', '|%s' % direct_url.split("|")[1])
                    except:
                        pass
                    play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            if self.downloadsubtitles:
                if subtitles:
                    try:
                        if not os.path.exists(os.path.join(self.base_path, "subtitles")):
                            errMsg = "Hiba a felirat könyvtár létrehozásakor!"
                            os.mkdir(os.path.join(self.base_path, "subtitles"))
                        for f in os.listdir(os.path.join(self.base_path, "subtitles")):
                            errMsg = "Hiba a korábbi feliratok törlésekor!"
                            os.remove(os.path.join(self.base_path, "subtitles", f))
                        xbmc.log('NetMozi: subtitle count: %d' % len(subtitles), xbmc.LOGINFO)
                        finalsubtitles = []
                        errMsg = "Hiba a sorozat felirat letöltésekor!"
                        for sub in subtitles:
                            subtitle = client.request(subtitles[sub])
                            if len(subtitle) > 0:
                                errMsg = "Hiba a sorozat felirat file kiírásakor!"
                                file = safeopen(os.path.join(self.base_path, "subtitles", "%s.srt" % sub.strip()), "w")
                                file.write(subtitle)
                                file.close()
                                errMsg = "Hiba a sorozat felirat file hozzáadásakor!"
                                finalsubtitles.append("%s/subtitles/%s.srt" % (self.base_path, sub.strip()))
                            else:
                                xbmc.log("NetMozi: Subtitles not found in source", xbmc.LOGERROR)
                        if len(finalsubtitles)>0:
                            errMsg = "Hiba a feliratok beállításakor!"
                            play_item.setSubtitles(finalsubtitles)
                    except:
                        xbmcgui.Dialog().notification("NetMozi hiba", errMsg, xbmcgui.NOTIFICATION_ERROR)
                        xbmc.log("Hiba a %s URL-hez tartozó felirat letöltésekor, hiba: %s" % (py2_encode(final_url), py2_encode(errMsg)), xbmc.LOGERROR)
                else:
                    xbmc.log("NetMozi: ResolveURL did not find any subtitles", xbmc.LOGINFO)
            xbmc.log('NetMozi: playing URL: %s' % direct_url, xbmc.LOGINFO)
            xbmcplugin.setResolvedUrl(syshandle, True, listitem=play_item)
        else:
            xbmc.log('NetMozi: ResolveURL could not resolve url: %s' % final_url, xbmc.LOGINFO)
            xbmcgui.Dialog().notification("URL feloldás hiba", "URL feloldása sikertelen a %s host-on" % urlparse.urlparse(final_url).hostname)

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

    def getCookiesWithoutLogin(Self):
        return client.request(base_url, output="cookie")

    def getCookiesWithLogin(self):
        login_url = '%s/login/do' % base_url
        login_cookies = client.request(login_url, post="username=%s&password=%s" % (quote_plus(self.username), quote_plus(self.password)), output='cookie')
        if 'ca=' in login_cookies:
            return login_cookies
        else:
            xbmcgui.Dialog().ok(u'NetMozi', u'Bejelentkez\u00E9si hiba! Érvénytelen felhasználó név/jelszó?')
            return None
        return

    def getSiteCookies(self):
        if (self.username and self.password) != '':
            return cache.get(self.getCookiesWithLogin, 24)
        else:
            return cache.get(self.getCookiesWithoutLogin, 24*365)

    def clearCache(self):
        cache.clear()
