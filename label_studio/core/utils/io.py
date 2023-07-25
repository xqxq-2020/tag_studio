import os
import socket
import ipaddress
import pkg_resources
import shutil
import glob
import io
import ujson as json
import itertools
import yaml

from urllib.parse import urlparse
from contextlib import contextmanager
from tempfile import mkstemp, mkdtemp

from appdirs import user_config_dir, user_data_dir, user_cache_dir


_DIR_APP_NAME = 'label-studio'


def good_path(path):
    return os.path.abspath(os.path.expanduser(path))


def find_node(package_name, node_path, node_type):
    assert node_type in ('dir', 'file', 'any')
    basedir = pkg_resources.resource_filename(package_name, '')
    node_path = os.path.join(*node_path.split('/'))  # linux to windows compatibility
    search_by_path = '/' in node_path or '\\' in node_path

    for path, dirs, filenames in os.walk(basedir):
        if node_type == 'file':
            nodes = filenames
        elif node_type == 'dir':
            nodes = dirs
        else:
            nodes = filenames + dirs
        if search_by_path:
            for found_node in nodes:
                found_node = os.path.join(path, found_node)
                if found_node.endswith(node_path):
                    return found_node
        elif node_path in nodes:
            return os.path.join(path, node_path)
    else:
        raise IOError(
            'Could not find "%s" at package "%s"' % (node_path, basedir)
        )


def find_file(file):
    return find_node('label_studio', file, 'file')


def find_dir(directory):
    return find_node('label_studio', directory, 'dir')


@contextmanager
def get_temp_file():
    fd, path = mkstemp()
    yield path
    os.close(fd)


@contextmanager
def get_temp_dir():
    dirpath = mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


def get_config_dir():
    config_dir = user_config_dir(appname=_DIR_APP_NAME)
    try:
        os.makedirs(config_dir, exist_ok=True)
    except OSError:
        pass
    return config_dir


def get_data_dir():
    data_dir = user_data_dir(appname=_DIR_APP_NAME)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_cache_dir():
    cache_dir = user_cache_dir(appname=_DIR_APP_NAME)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def delete_dir_content(dirpath):
    for f in glob.glob(dirpath + '/*'):
        remove_file_or_dir(f)


def remove_file_or_dir(path):
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def get_all_files_from_dir(d):
    out = []
    for name in os.listdir(d):
        filepath = os.path.join(d, name)
        if os.path.isfile(filepath):
            out.append(filepath)
    return out


def iter_files(root_dir, ext):
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith(ext):
                yield os.path.join(root, f)


def json_load(file, int_keys=False):
    with io.open(file, encoding='utf8') as f:
        data = json.load(f)
        if int_keys:
            return {int(k): v for k, v in data.items()}
        else:
            return data


def read_yaml(filepath):
    if not os.path.exists(filepath):
        filepath = find_file(filepath)
    with io.open(filepath, encoding='utf-8') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)  # nosec
    return data


def read_bytes_stream(filepath):
    with open(filepath, mode='rb') as f:
        return io.BytesIO(f.read())


def get_all_dirs_from_dir(d):
    out = []
    for name in os.listdir(d):
        filepath = os.path.join(d, name)
        if os.path.isdir(filepath):
            out.append(filepath)
    return out


class SerializableGenerator(list):
    """Generator that is serializable by JSON"""

    def __init__(self, iterable):
        tmp_body = iter(iterable)
        try:
            self._head = iter([next(tmp_body)])
            self.append(tmp_body)
        except StopIteration:
            self._head = []

    def __iter__(self):
        return itertools.chain(self._head, *self[:1])


def url_is_local(url):
    domain = urlparse(url).hostname
    try:
        ip = socket.gethostbyname(domain)
    except socket.error:
        from core.utils.exceptions import LabelStudioAPIException
        raise LabelStudioAPIException(f"Can't resolve hostname {domain}")
    else:
        if ip in (
            '0.0.0.0', # nosec
        ):
            return True
        local_subnets = [
            '127.0.0.0/8',
            '10.0.0.0/8',
            '172.16.0.0/12',
            '192.168.0.0/16',
        ]
        for subnet in local_subnets:
            if ipaddress.ip_address(ip) in ipaddress.ip_network(subnet):
                return True
        return False
