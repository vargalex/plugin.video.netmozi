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
import os,sys,re,xbmc,xbmcgui,xbmcplugin,xbmcaddon, locale, base64, random, string, json, time
from resources.lib.modules import client, control, cache, watched, linkpayload
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
loadLinks_url = base_url + "details/loadLinks/%s%s"
# A TV-kodos belepeshez a szerver tevesnek felismert User-Agentet var; a kulcsok a settings.xml tvdevice ertekei
tv_agents = {
    'Kodi (Smart TV)': 'Mozilla/5.0 (SMART-TV; Linux; Kodi) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Kodi/21.0',
    'Samsung TV (Tizen)': 'Mozilla/5.0 (SMART-TV; LINUX; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) Version/5.0 TV Safari/537.36',
    'LG TV (webOS)': 'Mozilla/5.0 (Web0S; Linux/SmartTV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 WebAppManager',
    'Android TV': 'Mozilla/5.0 (Linux; Android 11; SHIELD Android TV Build/RQ1A.210105.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/119.0.0.0 Mobile Safari/537.36',
}
# Python 2 alatt az X-Requested-With es az Accept fejlec Cloudflare 403-at valt ki, a szerver nelkuluk is JSON-t ad
xhr_headers = {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'} if sys.version_info[0] == 3 else {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
#track_url = '%s/visitortracker/track' % base_url

def mergeCookies(*cookieStrings):
    """"a=1; b=2" alaku suti-sztringek osszefesulese, a kesobbi felulirja a korabbit."""
    merged = {}
    for cs in cookieStrings:
        for item in (cs or '').split(';'):
            if '=' in item:
                name, value = item.strip().split('=', 1)
                merged[name] = value
    return '; '.join('%s=%s' % kv for kv in merged.items())

class CaptchaDialog(xbmcgui.WindowXMLDialog):
    """Sajat XML dialog (resources/skins/Default/720p/DialogCaptcha.xml): a captcha kep es ket gomb.
    A "Kod megadasa" gomb bezarja a dialogot (self.enter = True), a billentyuzetet a hivo nyitja."""
    IMAGE, ENTER, CANCEL = 20, 200, 201

    def __init__(self, *args, **kwargs):
        self.imgPath = kwargs['imgPath']
        self.enter = False

    def onInit(self):
        self.getControl(self.IMAGE).setImage(self.imgPath, False)
        self.setFocusId(self.ENTER)

    def onClick(self, controlId):
        if controlId == self.ENTER:
            self.enter = True
            self.close()
        elif controlId == self.CANCEL:
            self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):  # ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK
            self.close()

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
        self.markwatched = xbmcaddon.Addon().getSettingBool('markwatched')
        self.tvcodelogin = xbmcaddon.Addon().getSettingBool('tvcodelogin')
        self.tvdevice = xbmcaddon.Addon().getSetting('tvdevice')
        self.linkCookie = ''  # a mindjart oldal sutijei, a /links/open utak csak ezekkel ervenyesek
        self.base_path = py2_decode(control.transPath(control.addonInfo('profile')))
        self.searchFileName = os.path.join(self.base_path, "search.history")
        self.watched = watched.load() if self.markwatched else {}
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

        def getInfoData(infoRows, sample, regex, retIndex, defaultValue):
            if infoRows:
                for row in infoRows:
                    row = py2_encode(row)  # parseDOM Python 2 alatt unicode-ot ad, a minta str
                    if sample in row:
                        m = re.search(r"%s" % regex, row)
                        if m:
                            return m.group(retIndex)
            return defaultValue

        if search == None:
            search = ''
        cookies = self.getSiteCookies()
        url_content = linkpayload.resolveContent(client.request('%s?page=%s&type=%s&order=%s&search=%s' % (base_url, page, tipus, order, quote_plus(search)), cookie=cookies))
        if self.tvcodelogin and cookies and url_content and 'logout' not in url_content:
            # A cache-elt TV-kodos munkamenet lejart: uj belepes, majd ujra a lista
            cookies = cache.get(self.getCookiesWithTvCode, 0)
            if cookies:
                url_content = linkpayload.resolveContent(client.request('%s?page=%s&type=%s&order=%s&search=%s' % (base_url, page, tipus, order, quote_plus(search)), cookie=cookies))
        movies = client.parseDOM(url_content, 'div', attrs={'class': 'col-12.*?'})
        if not movies:
            resultsUrl = client.parseDOM(url_content, 'div', attrs={'id': 'indexListingAccess'}, ret='data-results-url')
            if resultsUrl:
                resultsUrl = resultsUrl[0]
                resultsToken = client.parseDOM(url_content, 'div', attrs={'id': 'indexListingAccess'}, ret='data-results-token')[0]
                content = client.request("%s%s" % (base_url, resultsUrl), post="token=%s" % resultsToken, cookie=self.getSiteCookies())
                data = json.loads(content   )
                if data["success"]:
                    url_content = py2_encode(linkpayload.resolveContent(data["html"]["classic"]))
                    movies = client.parseDOM(url_content, 'div', attrs={'class': 'col-12.*?'})
        if len(movies)>0:
            for movie in movies:
                m = re.search(r'(.*?)(title="[^"]*?")(.*)', movie, re.S)
                if m:
                    movie = "%s%s" % (m.group(1), m.group(3))
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
                year = getInfoData(infoRows, "Év:", "([0-9]{4})", 1, "")
                if year:
                    year = "(%s)" % year
                duration = int(getInfoData(infoRows, "Játékidő:", "([0-9]+) perc", 1, "0"))
                linkcount = getInfoData(infoRows, "Megtekintő linkek:", "([0-9]+)db", 1, "")
                if linkcount:
                    linkcount = " | [COLOR limegreen]%s link[/COLOR]" % linkcount
                action='series' if isSorozat else 'movie'
                meta = {'title': title, 'duration': duration, 'fanart': thumb}
                if not isSorozat and url in self.watched:
                    meta['playcount'] = 1
                self.addDirectoryItem('%s %s%s%s' % (title, year, sorozatLabel, linkcount), '%s&url=%s' % (action, url), thumb, 'DefaultMovies.png' if isSorozat else 'DefaultTVShows.png', meta=meta)
            pager = client.parseDOM(url_content, 'select', attrs={'name': 'page'})[0]
            options = client.parseDOM(pager, 'option', ret='value')
            if (int(options[-1]) > int(page)):
                self.addDirectoryItem(u'[I]K\u00F6vetkez\u0151 oldal  (%d/%s)>>[/I]' %(int(page)+1, options[-1]), 'movies&page=%d&type=%s&order=%s&search=%s' % (int(page)+1, tipus, order, search), '', 'DefaultFolder.png')
            self.endDirectory(type="movies")
        else:
            xbmcgui.Dialog().ok('NetMozi', 'Nem található forrás!')
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())

    def getSeries(self, url):
        url_content = linkpayload.resolveContent(client.request('%s%s' %(base_url, url), cookie=self.getSiteCookies()))
        container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
        temp = client.parseDOM(container, 'h3')[0]
        title = py2_encode(client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0])).strip()
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
        plot = self.getInfo(temp, 'Leírás')
        duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
        thumb = urlparse.urljoin(base_url, client.parseDOM(temp, 'img', ret='src')[0])
        series = client.parseDOM(url_content, 'ul', attrs={'id': 'seasonUl'})
        series = client.parseDOM(series, 'a', ret="data-season")
        for serie in series:
            self.addDirectoryItem('%s. évad' % py2_encode(serie), 'episodes&url=%s&serie=%s' % (url, serie), thumb, 'DefaultTVShows.png', meta={'title': '%s - %s. évad' % (title, py2_encode(serie)), 'plot': plot, 'duration': duration, 'fanart': thumb})
        self.endDirectory(type="movies")

    def getEpisodes(self, url, serie):
        url_content = linkpayload.resolveContent(client.request('%s%s' %(base_url, url), cookie=self.getSiteCookies()))
        container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
        temp = client.parseDOM(container, 'h3')[0]
        title = py2_encode(client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0])).strip()        
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
        plot = self.getInfo(temp, 'Leírás')
        duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
        temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
        thumb = urlparse.urljoin(base_url, client.parseDOM(temp, 'img', ret='src')[0])
        episodes = client.parseDOM(url_content, 'ul', attrs={'id': 'seasonUl%s' % serie})
        episodes = client.parseDOM(episodes, 'a', ret="data-episode")
        for episode in episodes:
            episodeUrl = '%s/s%s/e%s' % (url, serie, episode)
            meta = {'title': '%s - %s. évad %s. rész' % (title, py2_encode(serie), py2_encode(episode)), 'plot': plot, 'duration': duration, 'fanart': thumb}
            if episodeUrl in self.watched:
                meta['playcount'] = 1
            self.addDirectoryItem('%s. rész' % py2_encode(episode), 'movie&url=%s' % episodeUrl, thumb, 'DefaultTVShows.png', meta=meta)
        self.endDirectory(type="movies")

    def getMovieURL(self, content):
        movieURL = client.parseDOM(content, 'a', attrs={'class': 'details_links_btn'}, ret='href')
        if not movieURL:
            movieID = client.parseDOM(content, 'div', attrs={'data-link-loader': "*"}, ret='data-movie-id')
            if movieID:
                movieID = movieID[0]
                token = client.parseDOM(content, 'div', attrs={'data-link-loader': "*"}, ret='data-token')[0]
                csrf = client.parseDOM(content, 'div', attrs={'data-link-loader': "*"}, ret='data-csrf')[0]
                fURL = loadLinks_url % (movieID, csrf)
                content = client.request(loadLinks_url % (movieID, csrf), post="token=%s"  % token, cookie="%s;" % (self.getSiteCookies()), headers=dict(xhr_headers))
                if content:
                    data = json.loads(content)
                    if data["success"] == 1:
                        if data.get("linkPayload"):
                            movieURL = linkpayload.unpack(data["linkPayload"]["value"], token)
                        else:
                            movieURL = client.parseDOM(data["html"], 'a', attrs={'class': 'details_links_btn'}, ret='href')
        return movieURL

    def getLinkPage(self, url):
        """A mindjart.megnezed.com oldal lekérése. A rate limit (HTTP 429) captcha oldalát megoldatja a
        felhasználóval, majd újra kéri. Visszatérés: (tartalom, végső URL, payload scope, route-ok) vagy None."""
        for attempt in range(3):
            page = client.request(url, output='extended', error=True)
            if not page:
                return None
            content, _, _, cookie, final_url = page
            if sys.version_info[0] == 3 and isinstance(content, bytes):
                content = content.decode('utf-8', 'replace')
            if 'data-link-captcha' not in content:
                content = linkpayload.resolveContent(content)
                break
            if self.solveLinkCaptcha(content, url, cookie) is None:
                return None
        else:
            return None
        # A /links/open utak a vv oldal munkamenetehez kotottek (PHPSESSID, c): a suti nelkul a szerver
        # a 403-as 'nem hasznalhato' oldalt adja, a bongeszo is csak a sajat sutijeivel tudja megnyitni.
        self.linkCookie = cookie
        scope, routes = None, []
        payload = re.search(r'<script[^>]*data-link-payload[^>]*data-link-context="([^"]+)"[^>]*>(.*?)</script>', content, re.S)
        if payload:
            data = json.loads(payload.group(2))
            scope = data['scope']
            routes = linkpayload.unpack(data['value'], payload.group(1))
        return (content, final_url, scope, routes)

    def solveLinkCaptcha(self, content, url, cookie):
        """A captcha form kiolvasása, a kép letöltése és megjelenítése, a megoldás beküldése.
        True: elfogadva, False: hibás kód, None: megszakítva vagy ismeretlen oldal."""
        form = re.search(r'<form[^>]*data-link-captcha[^>]*data-endpoint="([^"]+)"', content)
        image = re.search(r'<img[^>]*src="([^"]+)"[^>]*data-link-captcha-image', content)
        fields = dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', content))
        if not form or not image or 'csrf_token' not in fields:
            xbmc.log('NetMozi: ismeretlen captcha oldal: %s' % url, xbmc.LOGWARNING)
            return None
        img = client.request(urlparse.urljoin(url, client.replaceHTMLCodes(image.group(1))), cookie=cookie, referer=url, output='extended', error=True)
        if not img:
            return None
        control.makeFile(control.dataPath)
        imgPath = os.path.join(control.dataPath, 'captcha.png')
        with open(imgPath, 'wb') as f:
            f.write(img[0])
        answer = self.askCaptcha(imgPath)
        if not answer:
            return None
        post = 'captcha=%s&csrf_token=%s&captcha_context=%s&token=%s' % (quote_plus(answer), quote_plus(fields['csrf_token']), quote_plus(fields.get('captcha_context', '')), quote_plus(fields.get('token', '')))
        result = client.request(urlparse.urljoin(url, form.group(1)), post=post, cookie=cookie, referer=url, headers=dict(xhr_headers))
        try:
            result = json.loads(result)
        except:
            result = {}
        if result.get('success') == 1:
            return True
        xbmcgui.Dialog().notification('NetMozi', result.get('error') or 'Hibás ellenőrző kód', xbmcgui.NOTIFICATION_ERROR)
        return False

    def askCaptcha(self, imgPath):
        """Kep a sajat dialogban, majd a Kodi billentyuzet. Ha a billentyuzetet megse-vel zarjak,
        a kep ujra megjelenik; a dialog Megse gombja vagy a Back szakitja meg."""
        while True:
            dialog = CaptchaDialog('DialogCaptcha.xml', control.addonPath, 'Default', '720p', imgPath=imgPath)
            dialog.doModal()
            enter = dialog.enter
            del dialog
            if not enter:
                return None
            keyboard = xbmc.Keyboard('', 'Írd be a képen látható 4 karaktert')
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText().strip():
                return keyboard.getText().strip().upper()

    def getMovie(self, url):
        # try:
        #     trackingData = json.loads(client.request(track_url, post='{"visitor_id": "%s", "fingerprint": "%s"}' % (self.visitorId, self.fingerprint)))
        #     if trackingData["status"] != "ok":
        #         xbmcgui.Dialog().ok('NetMozi', 'Hiba a tracking adatok lekérésekor!')
        #         xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
        #         return
        #     url_content = client.request('%s%s' %(base_url, url), cookie="%s; _vt_track=%s;" % (self.getSiteCookies(), trackingData["visitor_id"]))
        # except:
        url_content = linkpayload.resolveContent(client.request('%s%s' %(base_url, url), cookie="%s;" % (self.getSiteCookies())))
        if "regeljbe.png" in url_content:
            xbmcgui.Dialog().ok('NetMozi', 'Lista lekérés sikertelen. A hozzáféréshez regisztráció szükséges.')
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
        else:
            movieURL = self.getMovieURL(url_content)
            if movieURL:
                movieURL = movieURL[0]
            else:
                xbmcgui.Dialog().ok('NetMozi', 'Lista lekérés sikertelen.')
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
                return

            if movieURL.startswith("//"):
                movieURL = "https:%s" % movieURL
            container = client.parseDOM(url_content, 'div', attrs={'class': 'container'})[0]
            temp = client.parseDOM(container, 'h3')[0]
            title = py2_encode(client.replaceHTMLCodes(client.parseDOM(temp, 'a')[0])).strip()
            temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-4'})[0]
            thumb = urlparse.urljoin(base_url, client.parseDOM(temp, 'img', ret='src')[0])
            temp = client.parseDOM(container, 'div', attrs={'class': 'col-sm-8'})[0]
            plot = self.getInfo(temp, 'Leírás')
            duration = int(self.getInfo(temp, 'Játékidő:').replace(' perc', ''))*60
            serieInfo = client.parseDOM(url_content, 'h4')
            if serieInfo:
                serieInfo=' - %s' % py2_encode(serieInfo[0])
            else:
                serieInfo=''
            page = self.getLinkPage(movieURL)
            if not page:
                xbmcgui.Dialog().ok('NetMozi', 'Lista lekérés sikertelen.')
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
                return
            url_content, _, scope, routes = page
            card = client.parseDOM(url_content, 'div', attrs={'class': 'card .+?'})[0]
            tableDiv = client.parseDOM(card, 'div', attrs={'class': 'table-responsive'})[0]
            table = client.parseDOM(tableDiv, 'table', attrs={'class': 'table.*?'})
            if table:
                rows = re.findall(r'<tr([^>]*)>(.*?)</tr>', table[0], re.S)
                sourceCnt = 0
                titleWatched = url in self.watched
                for rowAttrs, row in rows:
                    cols = client.parseDOM(row, 'td')
                    if not cols:
                        continue
                    sourceCnt+=1
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
                    route = re.search(r'data-link-route="%s:([0-9]+)"' % scope, cols[3]) if scope else None
                    if route:
                        linkHref = routes[int(route.group(1))]
                    else:
                        linkHref=py2_encode(client.parseDOM(cols[3], 'a', attrs={'class': 'btn btn-outline-primary btn-sm action-btn'}, ret='href')[-1])
                    linkId=re.search(r'data-link-id="([^"]+)"', rowAttrs)
                    if linkId:
                        playUrl = url
                        playLinkId = linkId.group(1)
                    else:
                        mURL = urlparse.urlsplit(movieURL)
                        playUrl = urlparse.urljoin('%s://%s' % (mURL.scheme, mURL.netloc), linkHref)
                        playLinkId = ''
                    quality=py2_encode(cols[4].strip())
                    site=py2_encode(cols[5].strip())
                    meta = {'title': title + serieInfo, 'plot': plot, 'duration': duration, 'fanart': thumb}
                    if titleWatched:
                        meta['playcount'] = 1
                    self.addDirectoryItem('%s | [B]%s[/B] | [COLOR limegreen]%s[/COLOR] | [COLOR blue]%s[/COLOR] %s' % (format(sourceCnt, '02'), site, nyelv, quality, valid), 'playmovie&url=%s&linkid=%s&subtitled=%s' % (playUrl, playLinkId, 'true' if nyelv == 'Felirat' else 'false'), thumb, 'DefaultMovies.png', isFolder=False, meta=meta)
        self.endDirectory(type="movies")

    def getLinkURL(self, url, linkid):
        url_content = linkpayload.resolveContent(client.request('%s%s' % (base_url, url), cookie=self.getSiteCookies()))
        if not url_content:
            xbmcgui.Dialog().ok('NetMozi', 'Az oldal nem elérhető!')
            return None
        if "regeljbe.png" in url_content:
            xbmcgui.Dialog().ok('NetMozi', 'Lejátszás sikertelen. A hozzáféréshez regisztráció szükséges.')
            return None
        href = self.getMovieURL(url_content)
        if not href:
            xbmcgui.Dialog().ok('NetMozi', 'Törölt tartalom!')
            return None
        href = href[0]
        if href.startswith("//"):
            href = "https:%s" % href
        # A linkek sajat tokenje a mindjart oldal route listajabol jon, a film oldal tokenje ott nem ervenyes
        page = self.getLinkPage(href)
        if page and page[2]:
            row = re.search(r'<tr[^>]*data-link-id="%s"[^>]*>(.*?)</tr>' % re.escape(linkid), page[0], re.S)
            route = re.search(r'data-link-route="%s:([0-9]+)"' % page[2], row.group(1)) if row else None
            if route:
                return urlparse.urljoin(href, page[3][int(route.group(1))])
        xbmcgui.Dialog().ok('NetMozi', 'Törölt tartalom!')
        return None

    def playmovie(self, url, subtitled, linkid=None):
        titlePath = url if (linkid and self.markwatched) else None
        if linkid:
            url = self.getLinkURL(url, linkid)
            if not url:
                xbmcplugin.setResolvedUrl(syshandle, False, xbmcgui.ListItem())
                return
        xbmc.log('NetMozi: Try to play from URL: %s' % url, xbmc.LOGINFO)
        final_url = client.request(url, cookie=mergeCookies(self.getSiteCookies(), self.linkCookie), output="geturl", error=True)
        if final_url and "mindjart.megnezed" in final_url:
            # 429 eseten nincs redirect, a captcha megoldasa utan a getLinkPage adja az uj vegso URL-t
            page = self.getLinkPage(final_url)
            if not page:
                xbmcplugin.setResolvedUrl(syshandle, False, xbmcgui.ListItem())
                return
            url_content, final_url = page[0], page[1]
        if final_url:
            if "mindjart.megnezed" in final_url:
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
        import resolveurl
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
            if titlePath:
                watched.setPlaying(titlePath)
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
        """Bejelentkezes: a login oldal sutijei es a csrf-es form action kellenek a POST-hoz,
        a sikert a fooldal kijelentkezes linkje igazolja."""
        page = client.request(base_url + 'login', output='extended', error=True)
        if not page:
            xbmcgui.Dialog().ok(u'NetMozi', u'Bejelentkezési hiba! A login oldal nem elérhető.')
            return None
        content, _, _, cookies, _ = page
        if sys.version_info[0] == 3 and isinstance(content, bytes):
            content = content.decode('utf-8', 'replace')
        action = re.search(r'<form[^>]*action="(/login/do[^"]*)"', content)
        login_url = urlparse.urljoin(base_url, action.group(1) if action else '/login/do')
        result = client.request(login_url, post="username=%s&password=%s" % (quote_plus(self.username), quote_plus(self.password)), cookie=cookies, referer=base_url + 'login', output='extended', error=True)
        if result:
            cookies = mergeCookies(cookies, result[3])
            home = client.request(base_url, cookie=cookies)
            if home and 'logout' in home:
                return cookies
        xbmc.log('NetMozi: bejelentkezés sikertelen (login url: %s, válasz: %s)' % (login_url, 'nincs' if not result else len(result[0])), xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(u'NetMozi', u'Bejelentkez\u00E9si hiba! Érvénytelen felhasználó név/jelszó?')
        return None

    def getCookiesWithTvCode(self):
        """Eszkozkodos belepes (login/tv): a plugin tevekent ker egy kodot, a felhasznalo bejelentkezve
        a netmozi.com/login/tv oldalon jovahagyja, a plugin addig lekerdezi a login/tvPoll vegpontot."""
        tv_agent = tv_agents.get(self.tvdevice, tv_agents['Kodi (Smart TV)'])
        page = client.request(base_url + 'login/tv', output='extended', error=True, headers={'User-Agent': tv_agent})
        content = page[0] if page else None
        if sys.version_info[0] == 3 and isinstance(content, bytes):
            content = content.decode('utf-8', 'replace')
        csrf = re.search(r'data-tv-login data-csrf="([^"]+)"', content or '')
        if not csrf:
            if not content:
                reason = 'nincs válasz'
            elif 'Just a moment' in content or 'cf-chl' in content:
                reason = 'Cloudflare ellenőrző oldal (403)'
            elif 'csak TV-r' in content:
                reason = 'a szerver nem TV-ként ismerte fel a kérést'
            else:
                reason = 'ismeretlen tartalom'
            xbmc.log('NetMozi: TV-kódos belépés nem érhető el: %s (válasz hossza: %s, User-Agent: %s)' % (reason, len(content or ''), tv_agent), xbmc.LOGWARNING)
            xbmcgui.Dialog().ok(u'NetMozi', u'A TV-kódos belépés nem érhető el (%s).' % reason)
            return None
        cookies = page[3]
        headers = dict(xhr_headers, **{'User-Agent': tv_agent})
        start = client.request(base_url + 'login/tvStart' + csrf.group(1), post='', cookie=cookies, referer=base_url + 'login/tv', headers=dict(headers), output='extended', error=True)
        try:
            data = json.loads(start[0])
        except:
            data = {}
        if data.get('success') != 1:
            xbmcgui.Dialog().ok(u'NetMozi', data.get('error') or u'A belépési kód kérése sikertelen.')
            return None
        cookies = mergeCookies(cookies, start[3])
        interval = int(data.get('interval', 4))
        expires_in = int(data.get('expires_in', 600))
        deadline = time.time() + expires_in
        message = u'Egy másik eszközön nyisd meg a [B]netmozi.com/login/tv[/B] oldalt, jelentkezz be, és hagyd jóvá ezt a kódot:\n[B]%s[/B]' % data['code']
        progress = xbmcgui.DialogProgress()
        progress.create(u'NetMozi - Belépés TV-kóddal', message)
        status = 'cancelled'
        while time.time() < deadline:
            progress.update(int(100 * (deadline - time.time()) / expires_in), message)
            for _ in range(interval * 2):
                if progress.iscanceled():
                    break
                xbmc.sleep(500)
            if progress.iscanceled():
                status = 'cancelled'
                break
            poll = client.request(base_url + 'login/tvPoll' + csrf.group(1), post='', cookie=cookies, referer=base_url + 'login/tv', headers=dict(headers), output='extended', error=True)
            try:
                result = json.loads(poll[0])
            except:
                result = {}
            status = result.get('status', 'pending')
            if status == 'approved':
                cookies = mergeCookies(cookies, poll[3])
                break
            if status in ('expired', 'limit'):
                xbmcgui.Dialog().ok(u'NetMozi', result.get('message') or u'A belépési kód lejárt, kérj újat.')
                break
        progress.close()
        if status != 'approved':
            xbmc.log('NetMozi: TV-kódos belépés megszakadt (%s)' % status, xbmc.LOGINFO)
            return None
        home = client.request(base_url, cookie=cookies)
        if home and 'logout' in home:
            return cookies
        home = client.request(base_url, cookie=cookies, headers={'User-Agent': tv_agent})
        xbmc.log('NetMozi: TV-kódos belépés jóváhagyva, de a session az alap User-Agenttel nem bejelentkezett (TV User-Agenttel: %s)' % bool(home and 'logout' in home), xbmc.LOGWARNING)
        xbmcgui.Dialog().ok(u'NetMozi', u'A jóváhagyás megtörtént, de a bejelentkezett munkamenet nem használható. Kérlek jelezd a fejlesztőnek.')
        return None

    def getSiteCookies(self):
        if self.tvcodelogin:
            return cache.get(self.getCookiesWithTvCode, 24*365)
        elif (self.username and self.password) != '':
            return cache.get(self.getCookiesWithLogin, 24)
        else:
            return cache.get(self.getCookiesWithoutLogin, 24*365)

    def clearCache(self):
        cache.clear()

    def clearWatched(self):
        watched.clear()
