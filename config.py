import yaml
import logging

logging.basicConfig(level=logging.INFO)

configFile = 'config.yaml'

class ConfigError(BaseException):
    pass

try:

    config = yaml.load(open(configFile, encoding='utf-8'), Loader=yaml.FullLoader)

    username = config['username']
    password = config['password']
    if not username or not password:
        raise ValueError('empty username or password')

    refreshInterval = config['refreshInterval']
    if refreshInterval[0] < 3 or refreshInterval[1] < 1:
        raise ValueError('refreshInterval out of range')

    requestTimeout = config['requestTimeout']
    if requestTimeout is not None and requestTimeout < 0:
        raise ValueError('requestTimeout out of range')

    retryWaiting = config['retryWaiting']
    if retryWaiting < 0:
        raise ValueError('retryWaiting out of range')

    candidates = config['candidates']

except Exception as e:
    raise ConfigError(*e.args)
