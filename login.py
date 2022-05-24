import config
import session

class LoginError(RuntimeError):
    pass

class LoginPage:

    loginPageUrl = 'https://iaaa.pku.edu.cn/iaaa/oauth.jsp?appID=syllabus&appName=%E5%AD%A6%E7%94%9F%E9%80%89%E8%AF%BE%E7%B3%BB%E7%BB%9F&redirectUrl=http://elective.pku.edu.cn:80/elective2008/ssoLogin.do'
    loginSubmissionUrl = 'https://iaaa.pku.edu.cn/iaaa/oauthlogin.do'
    loginRedirectionUrl = 'http://elective.pku.edu.cn:80/elective2008/ssoLogin.do'

    def __init__(self):
        self.session = session.Session()

    def getLoginPage(self):
        return self.session.getDocument(self.loginPageUrl, headers={
            'Sec-Fetch-Site': 'none'
        })

    def getLoginData(self, username=config.username, password=config.password):
        return ({
            'appid': 'syllabus',
            'userName': username,
            'password': password,
            'randCode': '',
            'smsCode': '',
            'otpCode': '',
            'redirUrl': self.loginRedirectionUrl,
        })
    
    def submitLogin(self):
        return self.session.postAjax(self.loginSubmissionUrl, headers={
            'Origin': 'https://iaaa.pku.edu.cn',
            'Referer': self.loginPageUrl,
        }, data=self.getLoginData())

    def login(self):
        try:
            self.getLoginPage()
            submission = self.submitLogin().json()
        except Exception as e:
            raise LoginError(*e.args)
        if not submission['success']:
            raise LoginError('login not successful')
        return submission
