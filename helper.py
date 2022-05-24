import pickle
import lxml
import bs4
import random
import urllib.parse
import re
import logging

import login

def complementUrl(url, hint):
    parsedUrl = list(urllib.parse.urlparse(url))
    parsedHint = list(urllib.parse.urlparse(hint))
    for i in range(len(parsedUrl)):
        if not parsedUrl[i]:
            parsedUrl[i] = parsedHint[i]
    return urllib.parse.urlunparse(parsedUrl)

class PageError(RuntimeError):
    pass

class Page:

    def __init__(self, res):
        self.response = res
        self.text = self.response.text
        self.document = bs4.BeautifulSoup(self.text, 'lxml')

class HelperPage:

    sessionDumpfile = 'session.dat'
    pageUrl = 'https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/help/HelpController.jpf'
    pageUrlRoot = 'https://elective.pku.edu.cn'

    def __init__(self):
        try:
            self.loadSession()
            logging.info('try saved session: ' + self.sessionDumpfile)
            page = self.getPage()
            self.parsePage(page)
            logging.info('use saved session: ' + self.sessionDumpfile)
        except Exception:
            logging.info('new session logging in...')
            page = self.getPageFromLogin()
            self.parsePage(page)
            logging.info('new session logged in')
        self.page = page
        self.dumpSession()
        logging.info('session saved as: ' + self.sessionDumpfile)

    def loadSession(self):
        self.session = pickle.load(open(self.sessionDumpfile, 'rb'))

    def dumpSession(self):
        pickle.dump(self.session, open(self.sessionDumpfile, 'wb'))

    def getPage(self):
        return Page(self.session.getDocument(self.pageUrl))

    def parsePage(self, page):
        try:
            self.parseLinks(page)
            self.parsePersonal(page)
        except Exception as e:
            raise PageError(*e.args)

    def parseLinks(self, page):
        self.links = {}
        for a in page.document.findAll('a'):
            self.links[a.text.strip()] = complementUrl(a['href'], self.pageUrlRoot)

    def parsePersonal(self, page):
        personal = re.search(r'【.*?】', page.text)[0].split()[:2]
        personal[0] = personal[0][1:]
        logging.info('got personal information: ' + str(personal))
        self.personal = personal

    def getPageFromLogin(self):
        loginPage = login.LoginPage()
        submission = loginPage.login()
        self.session = loginPage.session
        return Page(self.session.getDocument(loginPage.loginRedirectionUrl, params={
            '_rand': str(random.random()),
            'token': submission['token'],
        }, headers={
            'Sec-Fetch-Site': 'same-site'
        }))
