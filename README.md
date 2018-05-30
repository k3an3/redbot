# Redbot
Redbot: an automated and distributed red team and traffic generation system. Using Python 3.6, Flask, Flask-SocketIO, and some basic frontend. Intended for use on GNU/Linux systems.

## Installation
Install the system dependencies below(for Debian-like systems), which will need to be installed on all hosts that will run part of Redbot. Additional packages may need to be
installed for all modules to function (e.g. the Metasploit framework).
```
# apt-get install -y lib{ffi,xml{sec1,2}}-dev python3-{setuptools,pip} nmap git
```
A single Redis server instance will need to be installed on a related system.

Clone the repository. Then, in the project's directory:
```
# pip3 install .
```
`pip3` may be substitututed with `pip` or `python3.x -m pip`, as necessary.

This will install the various binaries to the system such that they should be available in `$PATH`.

Systemd services for all components will be installed automatically, and they
can also be found in `scripts/`.

## Running
There are 3 main daemons that are part of Redbot, all of which need to be running to ensure proper functionality.

All daemons must share a single Redis instance. To configure this for each daemon (if Redis is not on the same machine), set the `REDIS_HOST` environment variable to the hostname or IP address of the Redis server.

### Redbot Web
This daemon provides the main web application and the core functionality of the application. Before running, it may be desirable or necessary to create and edit `redbot/settings_local.py`.

The daemon can be started with:

`# systemctl start redbot`

or

`$ redbot-web`

### Redbot Worker
The worker executes tasks to facilitate host discovery and attack/traffic generation.

It can be executed with:

`# systemctl start redbot-celery`

or 

`$ redbot-celery`

This script simply invokes Celery with a basic configuration that should be appropriate in basic deployments, allocating equal resources to both discovery and attack worker queues, and using the default worker count based on the current system's processor core count:

`celery -A redbot.core.async.celery worker --loglevel=info --pidfile=".%n.pid" -Q discovery,celery`

However, this may not allocate enough resources, causing deadlocks/backlogged tasks. It may be desirable to increase the worker count using the `-c` flag, e.g. `-c 100` for 100 worker processes. A large number of workers is usually fine on systems with a much lower core count, as many of the tasks in the application are I/O bound. Further, the number of workers can be tweaked to match exactly the number of targets (for discovery queues) and for attacks. A per-queue worker count can be specified; see the Celery Documentation (http://docs.celeryproject.org/en/latest/userguide/workers.html).

The Redbot worker can be run on as many systems as necessary, as long as they are all configured to talk to the the same Redis server instance, and are equipped with the proper dependencies and system configuration.

### Redbot Celery beat
Celery beat is used to kick off scheduled tasks every few seconds. This needs to have a single instance, and must be able to talk to the Redis server. 

It can be started with:


`# systemctl start redbot-celerybeat`

or 

`$ redbot-celerybeat`

## Documentation
For function-level documentation, Sphinx-compatible docstrings are included. To build the documentation, simply run `make` in the `docs/` directory and choose the desired output format.


