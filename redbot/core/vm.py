"""
Various utilities to handle scaling and deployment of Docker containers.
"""
import random
from typing import TextIO, Dict, List

from docker import DockerClient
from docker.models.images import Image
from machine import Machine

from redbot.core.models import storage
from redbot.core.utils import get_core_setting

images = []


def shell_unpack_kwargs(config: Dict[str, str], driver: str) -> List[str]:
    """
    Given a dictionary of configuration, properly modify the argument names for Docker Machine's CLI by prepending
    hyphens and the driver name.

    :param config: Dictionary of config items.
    :param driver: The Docker Machine driver to use.
    :return: List of the command line arguments to be passed to Docker Machine.
    """
    result = []
    for key, value in config.items():
        result.append('--' + driver + '-' + key)
        result.append(value)
    return result


def clean_machines() -> None:
    """
    Delete all Docker Machine instances that we are aware of.
    """
    m = Machine()
    for machine in storage.smembers('machines'):
        m.rm(machine=machine)


def get_docker_client(machine_name: str) -> DockerClient:
    """
    Given the name of a Docker Machine instance, return an instance of DockerClient that is configured to communicate
    with the machine.

    :param machine_name: Docker Machine instance name to interact with.
    :return: DockerClient instance configured for the machine.
    """
    m = Machine()
    return DockerClient(**m.config(machine=machine_name))


def deploy_docker_machine(machine_name: str, driver: str = 'vmwarevsphere',
                          config: Dict[str, str] = {}) -> (Machine, DockerClient):
    """
    Deploy a Docker Machine VM with the provided configuration.

    :param machine_name: The name of the new machine.
    :param driver: The Docker Machine driver to use.
    :param config: A dictionary of configuration values.
    :return: A tuple of the Machine and DockerClient instances that were created.
    """
    m = Machine()
    m.create(machine_name, driver=driver, blocking=True, xarg=shell_unpack_kwargs(config, driver))
    c = get_docker_client(machine_name)
    c.ping()
    storage.sadd('machines', machine_name)
    return m, c


def deploy_container(c: DockerClient, fileobj: TextIO = None) -> Image:
    """
    Deploy a docker container to an existing DockerClient instance, either by building the container or from an
    existing image file.

    :param c: The DockerClient instance to use.
    :param fileobj: Optionally, a file for an existing image.
    :return: The handle for the created image.
    """
    config = {
        'path': '.' if not fileobj else None,
        'dockerfile': 'Dockerfile.worker' if not fileobj else None,
        'fileobj': fileobj
    }
    image, _ = c.images.build(**config)
    return image


def deploy_worker(name: str = "", prebuilt: str = '') -> None:
    """
    Deploy a new Docker container to a new Docker Machine instance.

    :param name: Name of the new machine. If not provided, a name in the format redbot-n will be used, where n is the
    current number of machines known to Redbot.
    :param prebuilt: Whether the container should first be built locally,
    then shipped to the other machines, instead of building it on each machine.
    """
    config = {
        'vcenter': get_core_setting('vcenter_host'),
        'username': get_core_setting('vcenter_user'),
        'password': get_core_setting('vcenter_password'),
        'network': get_core_setting('vcenter_mgmt_network'),
        'network': get_core_setting('vcenter_attack_network'),
        'hostsystem': get_core_setting('vcenter_deploy_host'),
        'pool': get_core_setting('vcenter_pool'),
        'folder': get_core_setting('vcenter_folder'),
        'datastore': random.choice(get_core_setting('vcenter_datacenter').split(','))
    }
    print("Deploy with config", config)
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
        m, c = deploy_docker_machine('redbot-' + str(storage.scard('machines')), 'virtualbox')
        image = deploy_container(c)
    if image:
        file = image.save()

    # Deploy built image to target
    m, c = deploy_docker_machine(name or 'redbot-' + str(storage.scard('machines')), config=config)
    image = deploy_container(c, file)
    images.append(image)
