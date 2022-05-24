import urllib.parse
import logging
import random
import ddddocr
import time
import traceback

import config
import helper
from helper import complementUrl, Page, PageError

class ValidError(RuntimeError):
    pass

class ElectiveError(RuntimeError):
    pass

class SupplyPage:

    pageUrlRoot = helper.HelperPage.pageUrlRoot
    validCodeImageUrl = 'https://elective.pku.edu.cn/elective2008/DrawServlet'
    validationUrl = 'https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/validate.do'
    validationMaxtimes = 5
    refreshLimitUrl = 'https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/refreshLimit.do'

    def __init__(self):
        self.ddddocr = ddddocr.DdddOcr(show_ad=False)
        self.helperPage = helper.HelperPage()
        self.pageUrl = self.helperPage.links['补退选']
        self.studentId = urllib.parse.parse_qs(urllib.parse.urlparse(self.pageUrl).query)['xh'][0]
        self.session = self.helperPage.session
        self.refreshAll()
        self.matchCandidates()
        self.fillValidCode()

    def getFirstPage(self):
        logging.info('getting first page...')
        return Page(self.session.getDocument(self.pageUrl, headers={
            'Referer': helper.HelperPage.pageUrl
        }))

    def parseFirstPage(self, firstPage):
        self.parseCourseLists(firstPage)
        self.parsePageOptions(firstPage)
        self.firstPage = firstPage

    def parseCourseLists(self, page):
        t = 0
        for datagridHeader in page.document.findAll(class_='datagrid-header'):
            keys = [datagrid.text for datagrid in datagridHeader.findAll(class_='datagrid')]
            for datarow in datagridHeader.findNextSiblings(class_=['datagrid-even', 'datagrid-odd']):
                course = {}
                i = 0
                for datagrid in datarow.findAll(class_='datagrid'):
                    if keys[i] == '补选':
                        course[datagrid.text] = complementUrl(datagrid.find('a')['href'], self.pageUrlRoot)
                        i += 1
                        continue
                    course[keys[i]] = datagrid.text
                    if not i:
                        course['课程详细信息'] = complementUrl(datagrid.find('a')['href'], self.pageUrlRoot)
                        query = urllib.parse.urlparse(course['课程详细信息']).query
                        course['课程序列号'] = urllib.parse.parse_qs(query)['course_seq_no'][-1]
                    i += 1
                course['引用页'] = page.response.request.url
                self.courses[t][course['课程序列号']] = course
                logging.info('got course [' + str(t) + ']: (' + course['课程序列号'] + ') ' + course['课程名'])
            t += 1

    def parsePageOptions(self, page):
        for option in page.document.findAll('option'):
            parentAttributes = option.parent.attrs
            if 'name' in parentAttributes and parentAttributes['name'] == 'netui_row':
                if 'selected' in option.attrs:
                    self.firstPages.add(option['value'])
                else:
                    self.nextPages.add(option['value'])

    def getNextPage(self, pageOptionValue):
        logging.info('getting page ' + pageOptionValue + '...')
        return Page(self.session.getDocument(self.pageUrl, params={
            'netui_row': pageOptionValue
        }, headers={
            'Referer': self.pageUrl
        }))

    def refreshAll(self):
        self.courses = [{}, {}]
        self.firstPages = set()
        self.nextPages = set()
        firstPage = self.getFirstPage()
        self.parseFirstPage(firstPage)
        for pageOption in self.nextPages:
            nextPage = self.getNextPage(pageOption)
            self.parseCourseLists(nextPage)

    def getValidCodeImage(self):
        return self.session.getImage(self.validCodeImageUrl, params={
            'Rand': random.random() * 10000
        }, headers={
            'Referer': self.pageUrl
        })

    def recognizeValidCode(self, image):
        return self.ddddocr.classification(image.content)

    def validate(self, code=None):
        if code is None:
            if self.validCode is None:
                return false
            code = self.validCode
        return self.session.postAjax(self.validationUrl, headers={
            'Origin': self.pageUrlRoot,
            'Referer': self.pageUrl,
        }, data={
            'xh': self.studentId,
            'validCode': code,
        }).json()['valid'] == '2'

    def fillValidCode(self):
        for i in range(self.validationMaxtimes):
            try:
                image = self.getValidCodeImage()
                code = self.recognizeValidCode(image)
                if self.validate(code):
                    self.validCode = code
                    logging.info('got valid code: ' + code)
                    return
                raise ValidError('wrong valid code')
            except Exception as e:
                traceback.print_exc()
        raise ValidError('valid time run out')

    def refreshLimit(self, course):
        data = urllib.parse.parse_qs(urllib.parse.urlparse(course['刷新']).query)
        data = {
            'index': data['index'],
            'seq': data['seq'],
            'xh': data['xh'],
        }
        data = self.session.postAjax(self.refreshLimitUrl, headers={
            'Origin': self.pageUrlRoot,
            'Referer': course['引用页'],
        }, data=data).json()
        if data['electedNum'] == 'NA':  # 刷新频繁
            logging.error('(' + course['课程序列号'] + ') ' + course['课程名'] + ': 刷新频繁')
            return
        if data['electedNum'] == 'NB':  # 刷新异常
            logging.error('(' + course['课程序列号'] + ') ' + course['课程名'] + ': 刷新异常')
            return
        if int(data['electedNum']) < int(data['limitNum']):
            course['限数/已选'] = str(data['limitNum']) + ' / ' + str(data['electedNum'])
            course['补选'] = course['刷新']
            del course['刷新']
            logging.info('(' + course['课程序列号'] + ') ' + course['课程名'] + ': 检测到空余名额')
        else:
            logging.info('(' + course['课程序列号'] + ') ' + course['课程名'] + ': 没有空余名额')

    def elective(self, course):
        if not self.validate():
            self.fillValidCode()
        page = Page(self.session.getDocument(course['补选'], headers={
            'Referer': course['引用页']
        }))
        for img in page.document.findAll('img'):
            if img['src'].find('error.gif') != -1:
                raise ElectiveError(img.parent.parent.text)
        logging.info('(' + course['课程序列号'] + ') ' + course['课程名'] + ': 补选成功')

    def matchCandidates(self, candidates=config.candidates):
        self.candidates = {}
        for course in self.courses[0].values():
            priority = 1
            for candidate in candidates:
                for key in candidate:
                    if key == '优先级':
                        priority = int(candidate[key])
                        continue
                    if course[key] != str(candidate[key]):
                        break
                else:
                    if priority <= 0:
                        continue
                    logging.info('matched candidate: (' + course['课程序列号'] + ') ' + course['课程名'])
                    self.candidates[course['课程序列号']] = dict(**course, 优先级=priority)
                    break

    def refreshElectiveLoop(self, refreshInterval=config.refreshInterval):
        if not self.candidates:
            return
        candidates = {}
        prioritySum = 0
        for candidate in self.candidates.values():
            if '补选' in candidate:
                self.elective(candidate)
                return candidate
            priority = candidate['优先级']
            prioritySum += priority
            candidates[prioritySum] = candidate
        while True:
            randint = random.randint(0, prioritySum - 1)
            for p in candidates:
                if p > randint:
                    # TODO: rubustness
                    logging.info('try candidate: (' + candidates[p]['课程序列号'] + ') ' + candidates[p]['课程名'])
                    self.refreshLimit(candidates[p])
                    if '补选' in candidates[p]:
                        self.elective(candidates[p])
                        return candidates[p]
                    break
            sleepTime = refreshInterval[0] + refreshInterval[1] * random.random()
            logging.info('sleeping for ' + str(sleepTime) + ' seconds...')
            time.sleep(sleepTime)

if __name__ == '__main__':
    while True:
        try:
            supplyPage = SupplyPage()
            if not supplyPage.refreshElectiveLoop():
                logging.info('exiting for no candidate...')
                break
        except ImportError:
            raise
        except Exception:
            traceback.print_exc()
        except KeyboardInterrupt:
            logging.info('exiting on user interruption...')
            break
        sleepTime = config.retryWaiting
        logging.info('sleeping for ' + str(sleepTime) + ' seconds...')
        time.sleep(sleepTime)
