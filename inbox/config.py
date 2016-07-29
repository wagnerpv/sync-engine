import errno
import os
import yaml

# TODO[mike]: This should be removed once we've updated python to 2.7.9 which has better ssl support
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()

# TODO[mike]: This shold be removed once we've updated our base OS. openssl 1.0.1 doesn't support cross-signed certs
# https://github.com/certifi/python-certifi/issues/26#issuecomment-138322515
os.environ["REQUESTS_CA_BUNDLE"] = "/usr/local/lib/python2.7/dist-packages/certifi/weak.pem"

__all__ = ['config']


class ConfigError(Exception):

    def __init__(self, error=None, help=None):
        self.error = error or ''
        self.help = help or \
            'Run `sudo cp etc/config-dev.json /etc/inboxapp/config.json` and '\
            'retry.'

    def __str__(self):
        return '{0} {1}'.format(self.error, self.help)


class Configuration(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def get_required(self, key):
        if key not in self:
            raise ConfigError('Missing config value for {0}.'.format(key))

        return self[key]


def _update_config_from_env(config):
    """
    Update a config dictionary from configuration files specified in the
    environment.

    The environment variable `INBOX_CFG_PATH` contains a list of .json or .yml
    paths separated by colons.  The files are read in reverse order, so that
    the settings specified in the leftmost configuration files take precedence.
    (This is to emulate the behavior of the unix PATH variable, but the current
    implementation always reads all config files.)

    The following paths will always be appended:

    If `INBOX_ENV` is 'prod':
      /etc/inboxapp/secrets.yml:/etc/inboxapp/config.json

    If `INBOX_ENV` is 'test':
      {srcdir}/etc/secrets-test.yml:{srcdir}/etc/config-test.yml

    If `INBOX_ENV` is 'dev':
      {srcdir}/etc/secrets-dev.yml:{srcdir}/etc/config-dev.yml

    Missing files in the path will be ignored.

    """
    srcdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')

    if 'INBOX_ENV' in os.environ:
        assert os.environ['INBOX_ENV'] in ('dev', 'test', 'staging', 'prod'), \
            "INBOX_ENV must be either 'dev', 'test', staging, or 'prod'"
        env = os.environ['INBOX_ENV']
    else:
        env = 'prod'

    if env in ['prod', 'staging']:
        base_cfg_path = [
            '/etc/inboxapp/secrets.yml',
            '/etc/inboxapp/config.json',
        ]
    else:
        v = {'env': env, 'srcdir': srcdir}
        base_cfg_path = [
            '{srcdir}/etc/secrets-{env}.yml'.format(**v),
            '{srcdir}/etc/config-{env}.json'.format(**v),
        ]

    if 'INBOX_CFG_PATH' in os.environ:
        cfg_path = os.environ.get('INBOX_CFG_PATH', '').split(os.path.pathsep)
        cfg_path = list(p.strip() for p in cfg_path if p.strip())
    else:
        cfg_path = []

    path = cfg_path + base_cfg_path

    for filename in reversed(path):
        try:
            f = open(filename)
        except (IOError, OSError) as e:
            if e.errno != errno.ENOENT:
                raise
        else:
            with f:
                # this also parses json, which is a subset of yaml
                config.update(yaml.safe_load(f))


def _get_local_feature_flags(config):
    if os.environ.get('FEATURE_FLAGS') is not None:
        flags = os.environ.get('FEATURE_FLAGS').split()
    else:
        flags = config.get('FEATURE_FLAGS', '').split()
    config['FEATURE_FLAGS'] = flags


def _get_process_name(config):
    if os.environ.get('PROCESS_NAME') is not None:
        config['PROCESS_NAME'] = os.environ.get("PROCESS_NAME")

config = Configuration()
_update_config_from_env(config)
_get_local_feature_flags(config)
_get_process_name(config)
