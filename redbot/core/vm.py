from typing import TextIO, Dict

from docker import DockerClient
from docker.models.images import Image
from machine import Machine

from redbot.core.utils import get_core_setting, get_core_settings

machines = []
images = []


def shell_unpack_kwargs(config, driver):
    result = []
    for key, value in config.items():
        result.append('--' + driver + '-' + key)
        result.append(value)
    return result


def deploy_docker_machine(machine_name: str, driver: str = 'vmwarevsphere', machine_config: Dict[str, str] = {}):
    m = Machine()
    m.create(machine_name, driver=driver, blocking=True, xarg=shell_unpack_kwargs(machine_config, driver))
    c = DockerClient(**m.config(machine=machine_name))
    c.ping()
    machines.append((m, c))
    return m, c


def deploy_container(c: DockerClient, fileobj: TextIO = None) -> Image:
    config = {
        'path': '.' if not fileobj else None,
        'dockerfile': 'Dockerfile.worker' if not fileobj else None,
        'fileobj': fileobj
    }
    image, _ = c.images.build(**config)
    return image


def deploy_worker(prebuilt: str = ''):
    config = {
        'vcenter': get_core_setting('vcenter_host'),
        'username': get_core_setting('vcenter_user'),
        'password': get_core_setting('vcenter_password'),
        'network': get_core_setting('vcenter_network'),
        'hostsystem': get_core_setting('vcenter_deploy_host'),
        'pool': get_core_setting('vcenter_pool')
    }
    build_mode = get_core_setting('build_mode')
    file, image = None, None

    # Prepare Container Image
    if prebuilt:
        c = DockerClient()
        image = c.images.get(prebuilt)
    elif build_mode == 'local':
        c = DockerClient()
        image = deploy_container(c)
    elif build_mode == 'virtualbox':
        m, c = deploy_docker_machine('redbot-' + len(machines), 'virtualbox')
        image = deploy_container(c)
    if image:
        file = image.save()

    # Deploy built image to target
    m, c = deploy_docker_machine('redbot-' + len(machines), config=config)
    image = deploy_container(c, file)
    images.append(image)

